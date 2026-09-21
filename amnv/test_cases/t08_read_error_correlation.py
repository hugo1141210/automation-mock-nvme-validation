import time

from amnv.cancellation import CancellationToken
from amnv.config_loader import PROJECT_ROOT
from amnv.log_parser import (
    find_by_cid,
    find_by_lba,
    parse_log_file,
)
from amnv.models import TestResult
from amnv.runner import CommandRunner
from amnv.validator import (
    all_checks_passed,
    check_completion_status,
    check_equal,
)


TEST_ID = "T08"
TEST_NAME = "Read Error Correlation"

TEST_LBA = 300
EXPECTED_ERROR = "NAND_READ_FAIL"

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
    entries = []

    if _stop_requested(cancellation_token):
        return _aborted_result(
            start_time=start_time,
            stage="BEFORE_LOG_RESET",
            reason=cancellation_token.reason,
            checks=checks,
            commands=commands,
            entries=entries,
        )

    # -------------------------------------------------
    # Isolate this test's runtime firmware log.
    # -------------------------------------------------
    RUNTIME_LOG_FILE.unlink(
        missing_ok=True
    )

    runner = CommandRunner(
        cancellation_token=cancellation_token
    )

    # -------------------------------------------------
    # S10 - Deterministic NAND Read Failure
    # -------------------------------------------------
    if _stop_requested(cancellation_token):
        return _aborted_result(
            start_time=start_time,
            stage="BEFORE_READ",
            reason=cancellation_token.reason,
            checks=checks,
            commands=commands,
            entries=entries,
        )

    read_result = runner.execute(
        "READ",
        lba=TEST_LBA,
        length=1,
        fault=EXPECTED_ERROR,
    )

    commands["read"] = (
        read_result
    )

    if read_result.get(
        "aborted",
        False,
    ):
        return _aborted_result(
            start_time=start_time,
            stage="READ",
            reason=read_result.get(
                "abort_reason"
            ),
            checks=checks,
            commands=commands,
            entries=entries,
        )

    checks.append(
        check_completion_status(
            read_result,
            "FAILED",
        )
    )

    completion = read_result[
        "completion"
    ]

    command = read_result[
        "command"
    ]

    checks.extend(
        [
            check_equal(
                "Completion Error",
                completion["error"],
                EXPECTED_ERROR,
            ),
            check_equal(
                "Completion Data",
                completion["data"],
                None,
            ),
            check_equal(
                "Timed Out",
                read_result["timed_out"],
                False,
            ),
        ]
    )

    # -------------------------------------------------
    # S11 - Parse runtime firmware log
    # -------------------------------------------------
    if _stop_requested(cancellation_token):
        return _aborted_result(
            start_time=start_time,
            stage="BEFORE_LOG_PARSE",
            reason=cancellation_token.reason,
            checks=checks,
            commands=commands,
            entries=entries,
        )

    entries = parse_log_file(
        RUNTIME_LOG_FILE
    )

    checks.append(
        check_equal(
            "Runtime Log Entry Count",
            len(entries),
            1,
        )
    )

    if _stop_requested(cancellation_token):
        return _aborted_result(
            start_time=start_time,
            stage="BEFORE_CORRELATION",
            reason=cancellation_token.reason,
            checks=checks,
            commands=commands,
            entries=entries,
        )

    # -------------------------------------------------
    # S12 - CID Correlation
    # -------------------------------------------------
    cid_entries = find_by_cid(
        entries,
        command["cid"],
    )

    checks.append(
        check_equal(
            "CID Correlation Count",
            len(cid_entries),
            1,
        )
    )

    # -------------------------------------------------
    # S12 - LBA Correlation
    # -------------------------------------------------
    lba_entries = find_by_lba(
        entries,
        TEST_LBA,
    )

    checks.append(
        check_equal(
            "LBA Correlation Count",
            len(lba_entries),
            1,
        )
    )

    if cid_entries:
        log_entry = cid_entries[0]

        checks.extend(
            [
                check_equal(
                    "Log CID",
                    log_entry["CID"],
                    command["cid"],
                ),
                check_equal(
                    "Log Opcode",
                    log_entry["Opcode"],
                    command["opcode"],
                ),
                check_equal(
                    "Log LBA",
                    log_entry["LBA"],
                    command["lba"],
                ),
                check_equal(
                    "Log Status",
                    log_entry["Status"],
                    completion["status"],
                ),
                check_equal(
                    "Log Error",
                    log_entry["Error"],
                    completion["error"],
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
            "NAND_READ_FAIL completion "
            "correlates with firmware log "
            "by CID, LBA, status, and error"
        ),
        actual=(
            "Read error correlation passed"
            if passed
            else "One or more checks failed"
        ),
        duration_sec=duration_sec,
        details={
            "test_lba": TEST_LBA,
            "expected_error": EXPECTED_ERROR,
            "runtime_log_file": str(
                RUNTIME_LOG_FILE.relative_to(
                    PROJECT_ROOT
                )
            ),
            "checks": checks,
            "commands": commands,
            "log_entries": entries,
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
    entries: list,
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
            "NAND_READ_FAIL completion "
            "correlates with firmware log "
            "by CID, LBA, status, and error"
        ),
        actual=(
            f"Test aborted at {stage}: "
            f"{abort_reason}"
        ),
        duration_sec=duration_sec,
        details={
            "test_lba": TEST_LBA,
            "expected_error": EXPECTED_ERROR,
            "runtime_log_file": str(
                RUNTIME_LOG_FILE.relative_to(
                    PROJECT_ROOT
                )
            ),
            "checks": checks,
            "commands": commands,
            "log_entries": entries,
            "abort": {
                "stage": stage,
                "reason": abort_reason,
            },
        },
    )

