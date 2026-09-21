import time

from amnv.cancellation import CancellationToken
from amnv.models import TestResult
from amnv.runner import CommandRunner
from amnv.validator import (
    all_checks_passed,
    check_completion_status,
    check_equal,
)


TEST_ID = "T02"
TEST_NAME = "Normal Write / Readback"

TEST_LBA = 600
TEST_PATTERN = "T02_WRITE_READBACK"


def run(
    cancellation_token: CancellationToken | None = None,
) -> TestResult:
    start_time = time.monotonic()

    runner = CommandRunner(
        cancellation_token=cancellation_token
    )

    checks = []
    commands = {}

    if (
        cancellation_token is not None
        and cancellation_token.is_requested()
    ):
        return _aborted_result(
            start_time=start_time,
            stage="BEFORE_WRITE",
            reason=cancellation_token.reason,
            checks=checks,
            commands=commands,
        )

    # -------------------------------------------------
    # S05 - Write Command
    # -------------------------------------------------
    write_result = runner.execute(
        "WRITE",
        lba=TEST_LBA,
        length=1,
        data=TEST_PATTERN,
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
    # S04 - Read Command
    #
    # Validation must go through the READ interface.
    # Do not inspect mock_storage.json directly.
    # -------------------------------------------------
    if (
        cancellation_token is not None
        and cancellation_token.is_requested()
    ):
        return _aborted_result(
            start_time=start_time,
            stage="BEFORE_READ",
            reason=cancellation_token.reason,
            checks=checks,
            commands=commands,
        )

    read_result = runner.execute(
        "READ",
        lba=TEST_LBA,
        length=1,
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
        )

    checks.append(
        check_completion_status(
            read_result,
            "SUCCESS",
        )
    )

    read_data = read_result[
        "completion"
    ]["data"]

    checks.extend(
        [
            check_equal(
                "Readback LBA",
                read_data["lba"],
                TEST_LBA,
            ),
            check_equal(
                "Readback Length",
                read_data["length"],
                1,
            ),
            check_equal(
                "Readback Data",
                read_data["pattern"],
                TEST_PATTERN,
            ),
            check_equal(
                "Unwritten Flag",
                read_data["unwritten"],
                False,
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
            f"Write and read back "
            f"{TEST_PATTERN} at LBA {TEST_LBA}"
        ),
        actual=(
            "Write / Readback validation passed"
            if passed
            else "One or more checks failed"
        ),
        duration_sec=duration_sec,
        details={
            "test_lba": TEST_LBA,
            "test_pattern": TEST_PATTERN,
            "checks": checks,
            "commands": commands,
        },
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
            f"Write and read back "
            f"{TEST_PATTERN} at LBA {TEST_LBA}"
        ),
        actual=(
            f"Test aborted at {stage}: "
            f"{abort_reason}"
        ),
        duration_sec=duration_sec,
        details={
            "test_lba": TEST_LBA,
            "test_pattern": TEST_PATTERN,
            "checks": checks,
            "commands": commands,
            "abort": {
                "stage": stage,
                "reason": abort_reason,
            },
        },
    )

