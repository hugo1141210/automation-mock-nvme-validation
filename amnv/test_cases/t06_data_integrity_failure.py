import time

from amnv.cancellation import CancellationToken
from amnv.models import TestResult
from amnv.runner import CommandRunner
from amnv.validator import (
    all_checks_passed,
    check_completion_status,
    check_equal,
    check_not_equal,
)


TEST_ID = "T06"
TEST_NAME = "Data Integrity Failure"

TEST_LBA = 700
EXPECTED_PATTERN = "T06_EXPECTED_DATA"


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
            stage="BEFORE_WRITE",
            reason=cancellation_token.reason,
            checks=checks,
            commands=commands,
        )

    # -------------------------------------------------
    # S05 - Write known data
    # -------------------------------------------------
    write_result = runner.execute(
        "WRITE",
        lba=TEST_LBA,
        length=1,
        data=EXPECTED_PATTERN,
    )

    commands["write"] = (
        write_result
    )

    if write_result.get(
        "aborted",
        False,
    ):
        return _aborted_result(
            start_time=start_time,
            stage="WRITE",
            reason=write_result.get(
                "abort_reason"
            ),
            checks=checks,
            commands=commands,
        )

    checks.append(
        check_completion_status(
            write_result,
            "SUCCESS",
        )
    )

    # -------------------------------------------------
    # S04 + S09 - READ with Data Miscompare
    #
    # Controller completes READ successfully,
    # but FaultInjector corrupts the returned data.
    #
    # Therefore:
    # CQ Status = SUCCESS
    # Data Validation = mismatch detected
    # -------------------------------------------------
    if _stop_requested(cancellation_token):
        return _aborted_result(
            start_time=start_time,
            stage="BEFORE_FAULT_READ",
            reason=cancellation_token.reason,
            checks=checks,
            commands=commands,
        )

    fault_read_result = runner.execute(
        "READ",
        lba=TEST_LBA,
        length=1,
        fault="miscompare",
    )

    commands["fault_read"] = (
        fault_read_result
    )

    if fault_read_result.get(
        "aborted",
        False,
    ):
        return _aborted_result(
            start_time=start_time,
            stage="FAULT_READ",
            reason=fault_read_result.get(
                "abort_reason"
            ),
            checks=checks,
            commands=commands,
        )

    checks.append(
        check_completion_status(
            fault_read_result,
            "SUCCESS",
        )
    )

    fault_data = fault_read_result[
        "completion"
    ]["data"]

    checks.extend(
        [
            check_equal(
                "Fault Read LBA",
                fault_data["lba"],
                TEST_LBA,
            ),
            check_not_equal(
                "Data Miscompare Detection",
                fault_data["pattern"],
                EXPECTED_PATTERN,
            ),
            check_equal(
                "Fault Read Timed Out",
                fault_read_result["timed_out"],
                False,
            ),
        ]
    )

    # -------------------------------------------------
    # Verify that the miscompare fault only corrupted
    # the returned response and did not modify storage.
    # -------------------------------------------------
    if _stop_requested(cancellation_token):
        return _aborted_result(
            start_time=start_time,
            stage="BEFORE_VERIFY_READ",
            reason=cancellation_token.reason,
            checks=checks,
            commands=commands,
        )

    verify_read_result = runner.execute(
        "READ",
        lba=TEST_LBA,
        length=1,
    )

    commands["verify_read"] = (
        verify_read_result
    )

    if verify_read_result.get(
        "aborted",
        False,
    ):
        return _aborted_result(
            start_time=start_time,
            stage="VERIFY_READ",
            reason=verify_read_result.get(
                "abort_reason"
            ),
            checks=checks,
            commands=commands,
        )

    checks.append(
        check_completion_status(
            verify_read_result,
            "SUCCESS",
        )
    )

    verify_data = verify_read_result[
        "completion"
    ]["data"]

    checks.extend(
        [
            check_equal(
                "Stored Data Preserved",
                verify_data["pattern"],
                EXPECTED_PATTERN,
            ),
            check_equal(
                "Stored Data LBA",
                verify_data["lba"],
                TEST_LBA,
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
            "READ completes successfully but "
            "Validator detects returned data mismatch"
        ),
        actual=(
            "Data miscompare correctly detected"
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
            "READ completes successfully but "
            "Validator detects returned data mismatch"
        ),
        actual=(
            f"Test aborted at {stage}: "
            f"{abort_reason}"
        ),
        duration_sec=duration_sec,
        details={
            "test_lba": TEST_LBA,
            "expected_pattern": EXPECTED_PATTERN,
            "checks": checks,
            "commands": commands,
            "abort": {
                "stage": stage,
                "reason": abort_reason,
            },
        },
    )

