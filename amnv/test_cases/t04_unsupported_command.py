import time

from amnv.cancellation import CancellationToken
from amnv.models import TestResult
from amnv.runner import CommandRunner
from amnv.validator import (
    all_checks_passed,
    check_completion_status,
    check_equal,
)


TEST_ID = "T04"
TEST_NAME = "Unsupported Command"

TEST_OPCODE = "FORMAT"


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
            stage="BEFORE_COMMAND",
            reason=cancellation_token.reason,
            checks=checks,
            commands=commands,
        )

    # -------------------------------------------------
    # S07 - Unsupported Command
    #
    # The command is allowed to enter the SQ.
    # Mock Controller rejects the unsupported opcode
    # and returns a normal CQ Entry.
    # -------------------------------------------------
    command_result = runner.execute(
        TEST_OPCODE
    )

    commands["unsupported"] = (
        command_result
    )

    if command_result.get(
        "aborted",
        False,
    ):
        return _aborted_result(
            start_time=start_time,
            stage="UNSUPPORTED_COMMAND",
            reason=command_result.get(
                "abort_reason"
            ),
            checks=checks,
            commands=commands,
        )

    checks.append(
        check_completion_status(
            command_result,
            "UNSUPPORTED_COMMAND",
        )
    )

    completion = command_result[
        "completion"
    ]

    checks.extend(
        [
            check_equal(
                "Completion Error",
                completion["error"],
                "UNSUPPORTED_COMMAND",
            ),
            check_equal(
                "Completion Data",
                completion["data"],
                None,
            ),
            check_equal(
                "Timed Out",
                command_result["timed_out"],
                False,
            ),
            check_equal(
                "Submitted Opcode",
                command_result[
                    "command"
                ]["opcode"],
                TEST_OPCODE,
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
            f"{TEST_OPCODE} returns "
            "UNSUPPORTED_COMMAND"
        ),
        actual=(
            "Unsupported command correctly rejected"
            if passed
            else "One or more checks failed"
        ),
        duration_sec=duration_sec,
        details={
            "test_opcode": TEST_OPCODE,
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
            f"{TEST_OPCODE} returns "
            "UNSUPPORTED_COMMAND"
        ),
        actual=(
            f"Test aborted at {stage}: "
            f"{abort_reason}"
        ),
        duration_sec=duration_sec,
        details={
            "test_opcode": TEST_OPCODE,
            "checks": checks,
            "commands": commands,
            "abort": {
                "stage": stage,
                "reason": abort_reason,
            },
        },
    )

