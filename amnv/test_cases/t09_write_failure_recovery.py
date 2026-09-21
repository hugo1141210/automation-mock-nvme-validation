import time

from amnv.cancellation import CancellationToken
from amnv.config_loader import PROJECT_ROOT
from amnv.log_parser import (
    find_by_cid,
    parse_log_file,
)
from amnv.models import TestResult
from amnv.runner import CommandRunner
from amnv.validator import (
    all_checks_passed,
    check_completion_status,
    check_equal,
)


TEST_ID = "T09"
TEST_NAME = "Write Failure + Recovery"

TEST_LBA = 400
OLD_PATTERN = "OLD_PATTERN"
NEW_PATTERN = "T09_RECOVERED_DATA"
EXPECTED_ERROR = "NAND_PROGRAM_FAIL"

RUNTIME_LOG_FILE = (
    PROJECT_ROOT
    / "logs"
    / "runtime_fw.log"
)


def run(
    cancellation_token: CancellationToken | None = None,
) -> TestResult:
    start_time = time.monotonic()

    checks = []
    commands = {}
    failure_log_entries = []

    if _stop_requested(cancellation_token):
        return _aborted_result(
            start_time=start_time,
            stage="BEFORE_LOG_RESET",
            reason=cancellation_token.reason,
            checks=checks,
            commands=commands,
            failure_log_entries=failure_log_entries,
        )

    # -------------------------------------------------
    # Isolate runtime log for this test.
    # -------------------------------------------------
    RUNTIME_LOG_FILE.unlink(
        missing_ok=True
    )

    runner = CommandRunner(
        cancellation_token=cancellation_token
    )

    # -------------------------------------------------
    # S10 - NAND Program Failure
    #
    # WRITE must fail before storage is modified.
    # -------------------------------------------------
    if _stop_requested(cancellation_token):
        return _aborted_result(
            start_time=start_time,
            stage="BEFORE_FAILED_WRITE",
            reason=cancellation_token.reason,
            checks=checks,
            commands=commands,
            failure_log_entries=failure_log_entries,
        )

    failed_write_result = runner.execute(
        "WRITE",
        lba=TEST_LBA,
        length=1,
        data=NEW_PATTERN,
        fault=EXPECTED_ERROR,
    )

    commands["failed_write"] = (
        failed_write_result
    )

    if failed_write_result.get(
        "aborted",
        False,
    ):
        return _aborted_result(
            start_time=start_time,
            stage="FAILED_WRITE",
            reason=failed_write_result.get(
                "abort_reason"
            ),
            checks=checks,
            commands=commands,
            failure_log_entries=failure_log_entries,
        )

    checks.append(
        check_completion_status(
            failed_write_result,
            "FAILED",
        )
    )

    failed_completion = (
        failed_write_result["completion"]
    )

    failed_command = (
        failed_write_result["command"]
    )

    checks.extend(
        [
            check_equal(
                "Failed Write CID",
                failed_command["cid"],
                1,
            ),
            check_equal(
                "Program Failure Error",
                failed_completion["error"],
                EXPECTED_ERROR,
            ),
            check_equal(
                "Program Failure Data",
                failed_completion["data"],
                None,
            ),
            check_equal(
                "Program Failure Timed Out",
                failed_write_result[
                    "timed_out"
                ],
                False,
            ),
        ]
    )

    # -------------------------------------------------
    # S11 + S12
    # Runtime firmware log correlation
    # -------------------------------------------------
    if _stop_requested(cancellation_token):
        return _aborted_result(
            start_time=start_time,
            stage="BEFORE_LOG_PARSE",
            reason=cancellation_token.reason,
            checks=checks,
            commands=commands,
            failure_log_entries=failure_log_entries,
        )

    failure_log_entries = parse_log_file(
        RUNTIME_LOG_FILE
    )

    if _stop_requested(cancellation_token):
        return _aborted_result(
            start_time=start_time,
            stage="BEFORE_LOG_CORRELATION",
            reason=cancellation_token.reason,
            checks=checks,
            commands=commands,
            failure_log_entries=failure_log_entries,
        )

    cid_entries = find_by_cid(
        failure_log_entries,
        failed_command["cid"],
    )

    checks.append(
        check_equal(
            "Failure Log CID Count",
            len(cid_entries),
            1,
        )
    )

    if cid_entries:
        log_entry = cid_entries[0]

        checks.extend(
            [
                check_equal(
                    "Failure Log CID",
                    log_entry["CID"],
                    failed_command["cid"],
                ),
                check_equal(
                    "Failure Log Opcode",
                    log_entry["Opcode"],
                    "WRITE",
                ),
                check_equal(
                    "Failure Log LBA",
                    log_entry["LBA"],
                    TEST_LBA,
                ),
                check_equal(
                    "Failure Log Status",
                    log_entry["Status"],
                    "FAILED",
                ),
                check_equal(
                    "Failure Log Error",
                    log_entry["Error"],
                    EXPECTED_ERROR,
                ),
            ]
        )

    # -------------------------------------------------
    # Verify failed WRITE did not change storage.
    #
    # Use the normal READ interface instead of
    # inspecting mock_storage.json directly.
    # -------------------------------------------------
    if _stop_requested(cancellation_token):
        return _aborted_result(
            start_time=start_time,
            stage="BEFORE_VERIFY_OLD_READ",
            reason=cancellation_token.reason,
            checks=checks,
            commands=commands,
            failure_log_entries=failure_log_entries,
        )

    verify_old_result = runner.execute(
        "READ",
        lba=TEST_LBA,
        length=1,
    )

    commands["verify_old_read"] = (
        verify_old_result
    )

    if verify_old_result.get(
        "aborted",
        False,
    ):
        return _aborted_result(
            start_time=start_time,
            stage="VERIFY_OLD_READ",
            reason=verify_old_result.get(
                "abort_reason"
            ),
            checks=checks,
            commands=commands,
            failure_log_entries=failure_log_entries,
        )

    checks.append(
        check_completion_status(
            verify_old_result,
            "SUCCESS",
        )
    )

    old_data = verify_old_result[
        "completion"
    ]["data"]

    checks.extend(
        [
            check_equal(
                "Verify Old Data CID",
                verify_old_result[
                    "command"
                ]["cid"],
                2,
            ),
            check_equal(
                "Storage Unchanged",
                old_data["pattern"],
                OLD_PATTERN,
            ),
        ]
    )

    # -------------------------------------------------
    # S13 - Controller Reset
    #
    # Queue pointers reset,
    # CID progression must remain.
    # -------------------------------------------------
    if _stop_requested(cancellation_token):
        return _aborted_result(
            start_time=start_time,
            stage="BEFORE_CONTROLLER_RESET",
            reason=cancellation_token.reason,
            checks=checks,
            commands=commands,
            failure_log_entries=failure_log_entries,
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
                "Reset Outstanding CID",
                reset_after[
                    "outstanding_cids"
                ],
                [],
            ),
            check_equal(
                "CID Preserved Across Reset",
                reset_after["next_cid"],
                3,
            ),
        ]
    )

    # -------------------------------------------------
    # Recovery WRITE
    # -------------------------------------------------
    if _stop_requested(cancellation_token):
        return _aborted_result(
            start_time=start_time,
            stage="BEFORE_RETRY_WRITE",
            reason=cancellation_token.reason,
            checks=checks,
            commands=commands,
            failure_log_entries=failure_log_entries,
        )

    retry_write_result = runner.execute(
        "WRITE",
        lba=TEST_LBA,
        length=1,
        data=NEW_PATTERN,
    )

    commands["retry_write"] = (
        retry_write_result
    )

    if retry_write_result.get(
        "aborted",
        False,
    ):
        return _aborted_result(
            start_time=start_time,
            stage="RETRY_WRITE",
            reason=retry_write_result.get(
                "abort_reason"
            ),
            checks=checks,
            commands=commands,
            failure_log_entries=failure_log_entries,
        )

    checks.append(
        check_completion_status(
            retry_write_result,
            "SUCCESS",
        )
    )

    checks.append(
        check_equal(
            "Retry Write CID",
            retry_write_result[
                "command"
            ]["cid"],
            3,
        )
    )

    # -------------------------------------------------
    # Final readback
    # -------------------------------------------------
    if _stop_requested(cancellation_token):
        return _aborted_result(
            start_time=start_time,
            stage="BEFORE_READBACK",
            reason=cancellation_token.reason,
            checks=checks,
            commands=commands,
            failure_log_entries=failure_log_entries,
        )

    readback_result = runner.execute(
        "READ",
        lba=TEST_LBA,
        length=1,
    )

    commands["readback"] = (
        readback_result
    )

    if readback_result.get(
        "aborted",
        False,
    ):
        return _aborted_result(
            start_time=start_time,
            stage="READBACK",
            reason=readback_result.get(
                "abort_reason"
            ),
            checks=checks,
            commands=commands,
            failure_log_entries=failure_log_entries,
        )

    checks.append(
        check_completion_status(
            readback_result,
            "SUCCESS",
        )
    )

    readback_data = readback_result[
        "completion"
    ]["data"]

    checks.extend(
        [
            check_equal(
                "Readback CID",
                readback_result[
                    "command"
                ]["cid"],
                4,
            ),
            check_equal(
                "Readback LBA",
                readback_data["lba"],
                TEST_LBA,
            ),
            check_equal(
                "Recovered Data",
                readback_data["pattern"],
                NEW_PATTERN,
            ),
            check_equal(
                "Final Outstanding CID",
                readback_result[
                    "queue_state"
                ]["outstanding_cids"],
                [],
            ),
            check_equal(
                "Final SQ State",
                [
                    readback_result[
                        "queue_state"
                    ]["sq_head"],
                    readback_result[
                        "queue_state"
                    ]["sq_tail"],
                ],
                [2, 2],
            ),
            check_equal(
                "Final CQ State",
                [
                    readback_result[
                        "queue_state"
                    ]["cq_head"],
                    readback_result[
                        "queue_state"
                    ]["cq_tail"],
                ],
                [2, 2],
            ),
            check_equal(
                "Final Next CID",
                readback_result[
                    "queue_state"
                ]["next_cid"],
                5,
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
            "NAND_PROGRAM_FAIL preserves old data, "
            "correlates with firmware log, "
            "and succeeds after reset and retry"
        ),
        actual=(
            "Write failure / recovery validation passed"
            if passed
            else "One or more checks failed"
        ),
        duration_sec=duration_sec,
        details={
            "test_lba": TEST_LBA,
            "old_pattern": OLD_PATTERN,
            "new_pattern": NEW_PATTERN,
            "expected_error": EXPECTED_ERROR,
            "checks": checks,
            "commands": commands,
            "failure_log_entries": (
                failure_log_entries
            ),
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
    failure_log_entries: list,
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
            "NAND_PROGRAM_FAIL preserves old data, "
            "correlates with firmware log, "
            "and succeeds after reset and retry"
        ),
        actual=(
            f"Test aborted at {stage}: "
            f"{abort_reason}"
        ),
        duration_sec=duration_sec,
        details={
            "test_lba": TEST_LBA,
            "old_pattern": OLD_PATTERN,
            "new_pattern": NEW_PATTERN,
            "expected_error": EXPECTED_ERROR,
            "checks": checks,
            "commands": commands,
            "failure_log_entries":
                failure_log_entries,
            "abort": {
                "stage": stage,
                "reason": abort_reason,
            },
        },
    )

