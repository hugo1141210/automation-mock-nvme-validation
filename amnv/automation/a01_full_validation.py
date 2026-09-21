from __future__ import annotations

import time
import traceback
from collections.abc import Callable
from typing import Any

from amnv.cancellation import CancellationToken
from amnv.storage import MockStorage
from amnv.test_cases.t01_device_baseline import run as run_t01
from amnv.test_cases.t02_write_readback import run as run_t02
from amnv.test_cases.t03_invalid_read_range import run as run_t03
from amnv.test_cases.t04_unsupported_command import run as run_t04
from amnv.test_cases.t05_read_timeout_recovery import run as run_t05
from amnv.test_cases.t06_data_integrity_failure import run as run_t06
from amnv.test_cases.t07_firmware_log_parsing import run as run_t07
from amnv.test_cases.t08_read_error_correlation import run as run_t08
from amnv.test_cases.t09_write_failure_recovery import run as run_t09


SUITE_ID = "A01"
SUITE_NAME = "Full Validation"

TESTS = [
    ("T01", "Device Baseline Check", run_t01),
    ("T02", "Normal Write / Readback", run_t02),
    ("T03", "Invalid Read Range", run_t03),
    ("T04", "Unsupported Command", run_t04),
    ("T05", "Read Timeout + Recovery", run_t05),
    ("T06", "Data Integrity Failure", run_t06),
    ("T07", "Firmware Log Parsing", run_t07),
    ("T08", "Read Error Correlation", run_t08),
    ("T09", "Write Failure + Recovery", run_t09),
]


def _emit_progress(
    progress_callback: Callable[[dict[str, Any]], None] | None,
    event: dict[str, Any],
) -> None:
    if progress_callback is not None:
        progress_callback(event)


def _stop_requested(
    cancellation_token: CancellationToken | None,
) -> bool:
    return (
        cancellation_token is not None
        and cancellation_token.is_requested()
    )


def _normal_result_record(
    result: Any,
) -> dict[str, Any]:
    if hasattr(result, "to_dict"):
        result_dict = result.to_dict()

    elif isinstance(result, dict):
        result_dict = result

    else:
        raise TypeError(
            "Test result must provide to_dict() "
            "or already be a dict."
        )

    return {
        "test_id": result_dict["test_id"],
        "result": result_dict["result"],
        "duration_sec": result_dict.get(
            "duration_sec",
            0.0,
        ),
        "details": result_dict,
        "exception": None,
    }


def _error_result_record(
    test_id: str,
    test_name: str,
    exc: Exception,
    duration_sec: float,
) -> dict[str, Any]:
    return {
        "test_id": test_id,
        "result": "ERROR",
        "duration_sec": duration_sec,
        "details": {
            "test_id": test_id,
            "test_name": test_name,
            "result": "ERROR",
            "expected": "Test completes without exception",
            "actual": (
                f"{type(exc).__name__}: {exc}"
            ),
            "duration_sec": duration_sec,
            "details": {
                "checks": [],
            },
        },
        "exception": {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        },
    }


def _not_run_result_record(
    test_id: str,
    test_name: str,
) -> dict[str, Any]:
    return {
        "test_id": test_id,
        "result": "NOT_RUN",
        "duration_sec": 0.0,
        "details": {
            "test_id": test_id,
            "test_name": test_name,
            "result": "NOT_RUN",
            "expected": "Scheduled for execution",
            "actual": (
                "Not run because suite stop was requested"
            ),
            "duration_sec": 0.0,
            "details": {
                "checks": [],
            },
        },
        "exception": None,
    }


def _progress_event(
    record: dict[str, Any],
    event_type: str,
) -> dict[str, Any]:
    details = record.get(
        "details",
        {},
    )

    return {
        "suite_id": SUITE_ID,
        "event": event_type,
        "test_id": record["test_id"],
        "test_name": details.get(
            "test_name",
            record["test_id"],
        ),
        "result": record["result"],
        "duration_sec": record.get(
            "duration_sec",
            0.0,
        ),
    }


def _started_progress_event(
    test_id: str,
    test_name: str,
) -> dict[str, Any]:
    return {
        "suite_id": SUITE_ID,
        "event": "TEST_STARTED",
        "test_id": test_id,
        "test_name": test_name,
        "result": "STARTED",
        "duration_sec": 0.0,
    }


def _event_type_for_result(
    result: str,
) -> str:
    if result == "ABORTED":
        return "TEST_ABORTED"

    if result == "ERROR":
        return "TEST_ERROR"

    if result == "NOT_RUN":
        return "TEST_NOT_RUN"

    return "TEST_COMPLETED"


def _append_not_run_records(
    test_results: list[dict[str, Any]],
    remaining_tests: list[
        tuple[str, str, Callable[..., Any]]
    ],
    progress_callback: Callable[
        [dict[str, Any]],
        None,
    ]
    | None,
) -> None:
    for (
        remaining_id,
        remaining_name,
        _,
    ) in remaining_tests:
        record = _not_run_result_record(
            remaining_id,
            remaining_name,
        )

        test_results.append(
            record
        )

        _emit_progress(
            progress_callback,
            _progress_event(
                record,
                "TEST_NOT_RUN",
            ),
        )


def run(
    cancellation_token: CancellationToken | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """
    Run A01 sequentially with STOP v1 cancellation support.

    STOP v1 behavior:
    - The same CancellationToken is passed to every T01-T09 test.
    - A stop request before a test starts prevents that test
      and all remaining tests from running.
    - A test interrupted while running returns ABORTED.
    - After ABORTED, all remaining tests are recorded NOT_RUN.
    - If the active test finishes before cancellation takes
      effect, its PASS/FAIL/ERROR result is preserved.
    - Suite result becomes STOPPED only when execution actually
      stops before all scheduled work has completed.
    - Earlier PASS/FAIL/ERROR results remain counted.
    """

    suite_start = time.monotonic()

    token = (
        cancellation_token
        if cancellation_token is not None
        else CancellationToken()
    )

    storage_reset_at_start = False

    test_results: list[
        dict[str, Any]
    ] = []

    stopped = False

    # If Stop was already requested before A01 actually begins,
    # do not mutate storage or start any Test Case.
    if _stop_requested(token):
        stopped = True

        _append_not_run_records(
            test_results=test_results,
            remaining_tests=TESTS,
            progress_callback=progress_callback,
        )

    else:
        MockStorage().reset()
        storage_reset_at_start = True

        for index, (
            test_id,
            test_name,
            test_run,
        ) in enumerate(TESTS):

            # Stop between Test Cases:
            # current and remaining units have not started.
            if _stop_requested(token):
                stopped = True

                _append_not_run_records(
                    test_results=test_results,
                    remaining_tests=TESTS[index:],
                    progress_callback=progress_callback,
                )

                break

            _emit_progress(
                progress_callback,
                _started_progress_event(
                    test_id,
                    test_name,
                ),
            )

            test_start = time.monotonic()

            try:
                raw_result = test_run(
                    cancellation_token=token
                )

                record = _normal_result_record(
                    raw_result
                )

                event_type = (
                    _event_type_for_result(
                        record["result"]
                    )
                )

            except Exception as exc:
                duration_sec = (
                    time.monotonic()
                    - test_start
                )

                record = _error_result_record(
                    test_id=test_id,
                    test_name=test_name,
                    exc=exc,
                    duration_sec=duration_sec,
                )

                event_type = (
                    "TEST_ERROR"
                )

            test_results.append(
                record
            )

            _emit_progress(
                progress_callback,
                _progress_event(
                    record,
                    event_type,
                ),
            )

            # An actually interrupted Test Case is the clearest
            # signal that suite execution must stop now.
            if record["result"] == "ABORTED":
                stopped = True

                _append_not_run_records(
                    test_results=test_results,
                    remaining_tests=TESTS[
                        index + 1:
                    ],
                    progress_callback=progress_callback,
                )

                break

            # Completion wins:
            # PASS / FAIL / ERROR above is preserved.  If Stop
            # arrived just after completion, only later units are
            # prevented from starting.
            if (
                index + 1 < len(TESTS)
                and _stop_requested(token)
            ):
                stopped = True

                _append_not_run_records(
                    test_results=test_results,
                    remaining_tests=TESTS[
                        index + 1:
                    ],
                    progress_callback=progress_callback,
                )

                break

    total_tests = len(
        TESTS
    )

    passed = sum(
        1
        for item in test_results
        if item["result"]
        == "PASS"
    )

    failed = sum(
        1
        for item in test_results
        if item["result"]
        == "FAIL"
    )

    errors = sum(
        1
        for item in test_results
        if item["result"]
        == "ERROR"
    )

    aborted = sum(
        1
        for item in test_results
        if item["result"]
        == "ABORTED"
    )

    not_run = sum(
        1
        for item in test_results
        if item["result"]
        == "NOT_RUN"
    )

    # STOP v1 definition:
    # executed = every unit that actually started and produced
    # PASS / FAIL / ERROR / ABORTED.
    executed = (
        passed
        + failed
        + errors
        + aborted
    )

    if stopped:
        suite_result = "STOPPED"

    elif failed > 0 or errors > 0:
        suite_result = "FAIL"

    else:
        suite_result = "PASS"

    stop_reason = None

    if stopped:
        stop_reason = (
            token.reason
            or "User requested stop"
        )

    return {
        "suite_id": SUITE_ID,
        "suite_name": SUITE_NAME,
        "result": suite_result,

        # Existing / compatibility fields
        "total": total_tests,
        "total_tests": total_tests,
        "passed": passed,
        "failed": failed,

        # STOP v1 execution-control fields
        "executed": executed,
        "errors": errors,
        "aborted": aborted,
        "not_run": not_run,
        "stopped": stopped,
        "stop_reason": stop_reason,

        "duration_sec": (
            time.monotonic()
            - suite_start
        ),
        "storage_reset_at_start": (
            storage_reset_at_start
        ),
        "tests": test_results,
    }
