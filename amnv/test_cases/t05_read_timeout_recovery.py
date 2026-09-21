import time

from amnv.cancellation import CancellationToken
from amnv.models import TestResult
from amnv.runner import CommandRunner
from amnv.validator import (
    all_checks_passed,
    check_completion_status,
    check_equal,
)


TEST_ID = "T05"
TEST_NAME = "Read Timeout + Recovery"

TEST_LBA = 100
EXPECTED_PATTERN = "TEST_PATTERN_A"


def run(
    cancellation_token: CancellationToken | None = None,
) -> TestResult:
    start_time = time.monotonic()

    runner = CommandRunner(
        cancellation_token=cancellation_token
    )

    checks = []
    commands = {}

    if _stop_requested(cancellation_token):
        return _aborted_result(
            start_time=start_time,
            stage="BEFORE_INITIAL_READ",
            reason=cancellation_token.reason,
            checks=checks,
            commands=commands,
        )

    # -------------------------------------------------
    # S04 + S08
    #
    # Initial READ is intentionally timed out.
    #
    # Host must detect the timeout because no normal
    # Completion is returned by the Mock Controller.
    # -------------------------------------------------
    timeout_result = runner.execute(
        "READ",
        lba=TEST_LBA,
        length=1,
        fault="timeout",
    )

    commands["initial_read"] = (
        timeout_result
    )

    # If Stop interrupted the active timeout subprocess,
    # CommandRunner already terminated the child process
    # and reset queue/outstanding state.
    if timeout_result.get(
        "aborted",
        False,
    ):
        return _aborted_result(
            start_time=start_time,
            stage="INITIAL_READ",
            reason=timeout_result.get(
                "abort_reason"
            ),
            checks=checks,
            commands=commands,
        )

    checks.extend(
        [
            check_equal(
                "Initial CID",
                timeout_result["command"]["cid"],
                1,
            ),
            check_equal(
                "Host Timeout Status",
                timeout_result["host"]["status"],
                "TIMEOUT",
            ),
            check_equal(
                "Timed Out",
                timeout_result["timed_out"],
                True,
            ),
            check_equal(
                "Timeout Completion",
                timeout_result["completion"],
                None,
            ),
            check_equal(
                "Timeout Controller Result",
                timeout_result["controller_result"],
                None,
            ),
            check_equal(
                "Outstanding CID After Timeout",
                timeout_result[
                    "queue_state"
                ]["outstanding_cids"],
                [1],
            ),
            check_equal(
                "SQ State After Timeout",
                [
                    timeout_result[
                        "queue_state"
                    ]["sq_head"],
                    timeout_result[
                        "queue_state"
                    ]["sq_tail"],
                ],
                [1, 1],
            ),
            check_equal(
                "CQ State After Timeout",
                [
                    timeout_result[
                        "queue_state"
                    ]["cq_head"],
                    timeout_result[
                        "queue_state"
                    ]["cq_tail"],
                ],
                [0, 0],
            ),
            check_equal(
                "Next CID After Timeout",
                timeout_result[
                    "queue_state"
                ]["next_cid"],
                2,
            ),
        ]
    )

    # -------------------------------------------------
    # S13 - Controller Reset
    #
    # Reset clears SQ/CQ/outstanding state,
    # but CID progression must be preserved.
    # -------------------------------------------------
    # A normal timeout intentionally leaves the CID
    # outstanding. If Stop arrives after the timeout but
    # before the normal recovery reset, perform the reset
    # only as cancellation cleanup and do not continue.
    if _stop_requested(cancellation_token):
        reset_result = (
            runner.reset_controller()
        )

        commands[
            "abort_cleanup_reset"
        ] = reset_result

        return _aborted_result(
            start_time=start_time,
            stage="AFTER_TIMEOUT",
            reason=cancellation_token.reason,
            checks=checks,
            commands=commands,
        )

    reset_result = (
        runner.reset_controller()
    )

    commands["controller_reset"] = (
        reset_result
    )

    reset_after = reset_result["after"]

    checks.extend(
        [
            check_equal(
                "Reset SQ State",
                [
                    reset_after["sq_head"],
                    reset_after["sq_tail"],
                ],
                [0, 0],
            ),
            check_equal(
                "Reset CQ State",
                [
                    reset_after["cq_head"],
                    reset_after["cq_tail"],
                ],
                [0, 0],
            ),
            check_equal(
                "Outstanding CID After Reset",
                reset_after[
                    "outstanding_cids"
                ],
                [],
            ),
            check_equal(
                "CID Preserved Across Reset",
                reset_after["next_cid"],
                2,
            ),
        ]
    )

    # -------------------------------------------------
    # Recovery Retry
    #
    # Retry must use a new CID.
    # -------------------------------------------------
    if _stop_requested(cancellation_token):
        return _aborted_result(
            start_time=start_time,
            stage="BEFORE_RETRY",
            reason=cancellation_token.reason,
            checks=checks,
            commands=commands,
        )

    retry_result = runner.execute(
        "READ",
        lba=TEST_LBA,
        length=1,
    )

    commands["retry_read"] = (
        retry_result
    )

    if retry_result.get(
        "aborted",
        False,
    ):
        return _aborted_result(
            start_time=start_time,
            stage="RETRY_READ",
            reason=retry_result.get(
                "abort_reason"
            ),
            checks=checks,
            commands=commands,
        )

    checks.append(
        check_completion_status(
            retry_result,
            "SUCCESS",
        )
    )

    retry_completion = (
        retry_result["completion"]
    )

    checks.extend(
        [
            check_equal(
                "Retry CID",
                retry_completion["cid"],
                2,
            ),
            check_equal(
                "Retry Readback LBA",
                retry_completion[
                    "data"
                ]["lba"],
                TEST_LBA,
            ),
            check_equal(
                "Retry Readback Data",
                retry_completion[
                    "data"
                ]["pattern"],
                EXPECTED_PATTERN,
            ),
            check_equal(
                "Retry Timed Out",
                retry_result["timed_out"],
                False,
            ),
            check_equal(
                "Final Outstanding CID",
                retry_result[
                    "queue_state"
                ]["outstanding_cids"],
                [],
            ),
            check_equal(
                "Final SQ State",
                [
                    retry_result[
                        "queue_state"
                    ]["sq_head"],
                    retry_result[
                        "queue_state"
                    ]["sq_tail"],
                ],
                [1, 1],
            ),
            check_equal(
                "Final CQ State",
                [
                    retry_result[
                        "queue_state"
                    ]["cq_head"],
                    retry_result[
                        "queue_state"
                    ]["cq_tail"],
                ],
                [1, 1],
            ),
            check_equal(
                "Final Next CID",
                retry_result[
                    "queue_state"
                ]["next_cid"],
                3,
            ),
        ]
    )

    duration_sec = (
        time.monotonic()
        - start_time
    )

    passed = all_checks_passed(
        checks
    )

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        passed=passed,
        expected=(
            "Initial READ times out, "
            "Controller Reset clears queue state, "
            "and retry succeeds with a new CID"
        ),
        actual=(
            "Timeout / Reset / Retry validation passed"
            if passed
            else "One or more checks failed"
        ),
        duration_sec=duration_sec,
        details={
            "test_lba": TEST_LBA,
            "expected_pattern": EXPECTED_PATTERN,
            "checks": checks,
            "commands": commands,
        },
    )

def _stop_requested(
    cancellation_token: CancellationToken | None,
) -> bool:
    return (
        cancellation_token is not None
        and cancellation_token.is_requested()
    )


def _aborted_result(
    start_time: float,
    stage: str,
    reason: str | None,
    checks: list,
    commands: dict,
) -> TestResult:
    duration_sec = (
        time.monotonic()
        - start_time
    )

    abort_reason = (
        reason
        or "Cancellation requested"
    )

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        passed=False,
        status="ABORTED",
        expected=(
            "Initial READ times out, "
            "Controller Reset clears queue state, "
            "and retry succeeds with a new CID"
        ),
        actual=(
            f"Test aborted at {stage}: "
            f"{abort_reason}"
        ),
        duration_sec=duration_sec,
        details={
            "test_lba": TEST_LBA,
            "expected_pattern":
                EXPECTED_PATTERN,
            "checks": checks,
            "commands": commands,
            "abort": {
                "stage": stage,
                "reason": abort_reason,
            },
        },
    )

