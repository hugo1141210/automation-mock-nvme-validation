import time

from amnv.cancellation import CancellationToken
from amnv.models import TestResult
from amnv.runner import CommandRunner
from amnv.validator import (
    all_checks_passed,
    check_completion_status,
    check_equal,
)


TEST_ID = "T03"
TEST_NAME = "Invalid Read Range"

TEST_LBA = 4095
TEST_LENGTH = 2


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
            stage="BEFORE_READ",
            reason=cancellation_token.reason,
            checks=checks,
            commands=commands,
        )

    # -------------------------------------------------
    # S04 + S06
    #
    # The READ command itself is structurally valid,
    # but LBA + Length exceeds device capacity.
    #
    # Valid device LBA range:
    # 0 ~ 4095
    #
    # Requested:
    # LBA 4095, Length 2
    # -> blocks 4095 and 4096
    # -> 4096 is out of range
    # -------------------------------------------------
    read_result = runner.execute(
        "READ",
        lba=TEST_LBA,
        length=TEST_LENGTH,
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
            "INVALID_RANGE",
        )
    )

    completion = read_result[
        "completion"
    ]

    checks.extend(
        [
            check_equal(
                "Completion Error",
                completion["error"],
                "INVALID_RANGE",
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
            f"READ LBA {TEST_LBA}, "
            f"Length {TEST_LENGTH} "
            "returns INVALID_RANGE"
        ),
        actual=(
            "Invalid range correctly rejected"
            if passed
            else "One or more checks failed"
        ),
        duration_sec=duration_sec,
        details={
            "test_lba": TEST_LBA,
            "test_length": TEST_LENGTH,
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
            f"READ LBA {TEST_LBA}, "
            f"Length {TEST_LENGTH} "
            "returns INVALID_RANGE"
        ),
        actual=(
            f"Test aborted at {stage}: "
            f"{abort_reason}"
        ),
        duration_sec=duration_sec,
        details={
            "test_lba": TEST_LBA,
            "test_length": TEST_LENGTH,
            "checks": checks,
            "commands": commands,
            "abort": {
                "stage": stage,
                "reason": abort_reason,
            },
        },
    )

