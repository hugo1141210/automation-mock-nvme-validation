import time

from amnv.cancellation import CancellationToken
from amnv.config_loader import (
    load_validation_config,
)
from amnv.models import TestResult
from amnv.runner import CommandRunner
from amnv.validator import (
    all_checks_passed,
    check_completion_status,
    check_equal,
    check_maximum,
)


TEST_ID = "T01"
TEST_NAME = "Device Baseline Check"


def run(
    cancellation_token: CancellationToken | None = None,
) -> TestResult:
    start_time = time.monotonic()

    config = load_validation_config()

    expected_device = config[
        "expected_device"
    ]

    health_thresholds = config[
        "health_thresholds"
    ]

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
            stage="BEFORE_IDENTIFY",
            reason=cancellation_token.reason,
            checks=checks,
            commands=commands,
        )

    # -------------------------------------------------
    # S01 - Identify Command
    # -------------------------------------------------
    identify_result = runner.execute(
        "IDENTIFY"
    )

    commands["identify"] = (
        identify_result
    )

    if identify_result.get(
        "aborted",
        False,
    ):
        return _aborted_result(
            start_time=start_time,
            stage="IDENTIFY",
            reason=identify_result.get(
                "abort_reason"
            ),
            checks=checks,
            commands=commands,
        )

    checks.append(
        check_completion_status(
            identify_result,
            "SUCCESS",
        )
    )

    identify_data = identify_result[
        "completion"
    ]["data"]

    checks.extend(
        [
            check_equal(
                "Model",
                identify_data["model"],
                expected_device["model"],
            ),
            check_equal(
                "Firmware Revision",
                identify_data[
                    "firmware_revision"
                ],
                expected_device[
                    "firmware_revision"
                ],
            ),
            check_equal(
                "NSID",
                identify_data["nsid"],
                expected_device["nsid"],
            ),
            check_equal(
                "Capacity Blocks",
                identify_data[
                    "capacity_blocks"
                ],
                expected_device[
                    "capacity_blocks"
                ],
            ),
            check_equal(
                "Logical Block Size",
                identify_data[
                    "logical_block_size_bytes"
                ],
                expected_device[
                    "logical_block_size_bytes"
                ],
            ),
        ]
    )

    # -------------------------------------------------
    # S03 - SMART / Health
    # -------------------------------------------------
    if (
        cancellation_token is not None
        and cancellation_token.is_requested()
    ):
        return _aborted_result(
            start_time=start_time,
            stage="BEFORE_SMART",
            reason=cancellation_token.reason,
            checks=checks,
            commands=commands,
        )

    smart_result = runner.execute(
        "SMART"
    )

    commands["smart"] = (
        smart_result
    )

    if smart_result.get(
        "aborted",
        False,
    ):
        return _aborted_result(
            start_time=start_time,
            stage="SMART",
            reason=smart_result.get(
                "abort_reason"
            ),
            checks=checks,
            commands=commands,
        )

    checks.append(
        check_completion_status(
            smart_result,
            "SUCCESS",
        )
    )

    health_data = smart_result[
        "completion"
    ]["data"]

    checks.extend(
        [
            check_maximum(
                "Temperature",
                health_data[
                    "temperature_c"
                ],
                health_thresholds[
                    "max_temperature_c"
                ],
            ),
            check_equal(
                "Critical Warning",
                health_data[
                    "critical_warning"
                ],
                health_thresholds[
                    "expected_critical_warning"
                ],
            ),
            check_equal(
                "Media Errors",
                health_data[
                    "media_errors"
                ],
                health_thresholds[
                    "expected_media_errors"
                ],
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
        expected="Device baseline matches configuration",
        actual=(
            "Baseline validation passed"
            if passed
            else "One or more checks failed"
        ),
        duration_sec=duration_sec,
        details={
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
            "Device baseline matches configuration"
        ),
        actual=(
            f"Test aborted at {stage}: "
            f"{abort_reason}"
        ),
        duration_sec=duration_sec,
        details={
            "checks": checks,
            "commands": commands,
            "abort": {
                "stage": stage,
                "reason": abort_reason,
            },
        },
    )

