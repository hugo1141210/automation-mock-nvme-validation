import time

from amnv.cancellation import CancellationToken
from amnv.config_loader import (
    PROJECT_ROOT,
    load_validation_config,
)
from amnv.log_parser import (
    find_by_cid,
    find_by_lba,
    parse_log_file,
)
from amnv.models import TestResult
from amnv.validator import (
    all_checks_passed,
    check_equal,
)


TEST_ID = "T07"
TEST_NAME = "Firmware Log Parsing"

LOG_FILE = (
    PROJECT_ROOT
    / "data"
    / "sample_fw.log"
)


def run(
    cancellation_token: CancellationToken | None = None,
) -> TestResult:
    start_time = time.monotonic()

    checks = []
    entries = []

    if _stop_requested(cancellation_token):
        return _aborted_result(
            start_time=start_time,
            stage="BEFORE_PARSE",
            reason=cancellation_token.reason,
            checks=checks,
            entries=entries,
        )

    config = load_validation_config()

    required_fields = config[
        "logging"
    ]["firmware_log_required_fields"]

    entries = parse_log_file(
        LOG_FILE
    )

    # -------------------------------------------------
    # Basic file parsing
    # -------------------------------------------------
    checks.append(
        check_equal(
            "Parsed Entry Count",
            len(entries),
            10,
        )
    )

    if _stop_requested(cancellation_token):
        return _aborted_result(
            start_time=start_time,
            stage="AFTER_PARSE",
            reason=cancellation_token.reason,
            checks=checks,
            entries=entries,
        )

    # -------------------------------------------------
    # Required fields
    # -------------------------------------------------
    expected_fields = set(
        required_fields
    )

    every_entry_has_required_fields = all(
        expected_fields.issubset(
            entry.keys()
        )
        for entry in entries
    )

    checks.append(
        check_equal(
            "Required Fields Present",
            every_entry_has_required_fields,
            True,
        )
    )

    if _stop_requested(cancellation_token):
        return _aborted_result(
            start_time=start_time,
            stage="BEFORE_CID_VALIDATION",
            reason=cancellation_token.reason,
            checks=checks,
            entries=entries,
        )

    # -------------------------------------------------
    # Verify known READ failure entry
    #
    # sample_fw.log:
    # CID 5 / READ / LBA 300 /
    # FAILED / NAND_READ_FAIL
    # -------------------------------------------------
    cid_5_entries = find_by_cid(
        entries,
        5,
    )

    checks.append(
        check_equal(
            "CID 5 Entry Count",
            len(cid_5_entries),
            1,
        )
    )

    if cid_5_entries:
        cid_5 = cid_5_entries[0]

        checks.extend(
            [
                check_equal(
                    "CID 5 Opcode",
                    cid_5["Opcode"],
                    "READ",
                ),
                check_equal(
                    "CID 5 LBA",
                    cid_5["LBA"],
                    300,
                ),
                check_equal(
                    "CID 5 Status",
                    cid_5["Status"],
                    "FAILED",
                ),
                check_equal(
                    "CID 5 Error",
                    cid_5["Error"],
                    "NAND_READ_FAIL",
                ),
            ]
        )

    if _stop_requested(cancellation_token):
        return _aborted_result(
            start_time=start_time,
            stage="BEFORE_LBA_VALIDATION",
            reason=cancellation_token.reason,
            checks=checks,
            entries=entries,
        )

    # -------------------------------------------------
    # Verify LBA lookup
    # -------------------------------------------------
    lba_2000_entries = find_by_lba(
        entries,
        2000,
    )

    checks.append(
        check_equal(
            "LBA 2000 Entry Count",
            len(lba_2000_entries),
            1,
        )
    )

    if lba_2000_entries:
        lba_2000 = (
            lba_2000_entries[0]
        )

        checks.extend(
            [
                check_equal(
                    "LBA 2000 Opcode",
                    lba_2000["Opcode"],
                    "WRITE",
                ),
                check_equal(
                    "LBA 2000 Error",
                    lba_2000["Error"],
                    "NAND_PROGRAM_FAIL",
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
            "Firmware log entries are parsed "
            "into structured fields correctly"
        ),
        actual=(
            "Firmware log parsing passed"
            if passed
            else "One or more checks failed"
        ),
        duration_sec=duration_sec,
        details={
            "log_file": str(
                LOG_FILE.relative_to(
                    PROJECT_ROOT
                )
            ),
            "parsed_entry_count": len(
                entries
            ),
            "checks": checks,
            "entries": entries,
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
            "Firmware log entries are parsed "
            "into structured fields correctly"
        ),
        actual=(
            f"Test aborted at {stage}: "
            f"{abort_reason}"
        ),
        duration_sec=duration_sec,
        details={
            "log_file": str(
                LOG_FILE.relative_to(
                    PROJECT_ROOT
                )
            ),
            "parsed_entry_count": len(entries),
            "checks": checks,
            "entries": entries,
            "abort": {
                "stage": stage,
                "reason": abort_reason,
            },
        },
    )

