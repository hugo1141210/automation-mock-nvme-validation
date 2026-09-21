from __future__ import annotations

import hashlib
import json
import time
import traceback
from pathlib import Path
from collections.abc import Callable
from typing import Any

from amnv.cancellation import CancellationToken
from amnv.config_loader import PROJECT_ROOT, load_validation_config
from amnv.log_parser import find_by_cid, parse_log_file
from amnv.runner import CommandRunner
from amnv.storage import MockStorage
from amnv.validator import all_checks_passed, check_equal


SUITE_ID = "A02"
SUITE_NAME = "Automated Fault Injection Campaign"
RUNTIME_LOG_FILE = PROJECT_ROOT / "logs" / "runtime_fw.log"


def _add(
    checks: list[dict[str, Any]],
    name: str,
    actual: Any,
    expected: Any,
) -> None:
    checks.append(
        check_equal(
            name,
            actual,
            expected,
        )
    )


def _load_campaign() -> dict[str, Any]:
    config = load_validation_config()

    path = (
        PROJECT_ROOT
        / config["automation"]["a02"]["campaign_file"]
    )

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def _storage_path() -> Path:
    config = load_validation_config()

    return (
        PROJECT_ROOT
        / config["storage"]["runtime_file"]
    )


def _storage_hash() -> str:
    return hashlib.sha256(
        _storage_path().read_bytes()
    ).hexdigest()


def _clear_runtime_log() -> None:
    RUNTIME_LOG_FILE.unlink(
        missing_ok=True
    )


def _ordered_cases(
    campaign: dict[str, Any],
) -> list[dict[str, Any]]:

    order = {
        name: index
        for index, name in enumerate(
            campaign["execution_order"]
        )
    }

    for case in campaign["cases"]:
        if case.get("profile_id") not in order:
            raise ValueError(
                "Unknown or missing profile_id "
                f"for {case.get('case_id')}: "
                f"{case.get('profile_id')}"
            )

    return sorted(
        campaign["cases"],
        key=lambda case: order[
            case["profile_id"]
        ],
    )


class _CaseCancelled(Exception):
    def __init__(
        self,
        stage: str,
        reason: str | None,
        *,
        checks: list[dict[str, Any]] | None = None,
        setup: dict[str, Any] | None = None,
        evidence: dict[str, Any] | None = None,
    ) -> None:
        self.stage = stage
        self.reason = (
            reason
            or "User requested stop"
        )
        self.checks = checks or []
        self.setup = setup
        self.evidence = evidence or {}

        super().__init__(
            f"{stage}: {self.reason}"
        )


def _stop_requested(
    cancellation_token: CancellationToken | None,
) -> bool:
    return (
        cancellation_token is not None
        and cancellation_token.is_requested()
    )


def _raise_if_cancelled(
    cancellation_token: CancellationToken | None,
    stage: str,
    *,
    checks: list[dict[str, Any]] | None = None,
    setup: dict[str, Any] | None = None,
    evidence: dict[str, Any] | None = None,
) -> None:
    if not _stop_requested(
        cancellation_token
    ):
        return

    raise _CaseCancelled(
        stage=stage,
        reason=(
            cancellation_token.reason
            if cancellation_token is not None
            else None
        ),
        checks=checks,
        setup=setup,
        evidence=evidence,
    )


def _emit_progress(
    progress_callback: Callable[
        [dict[str, Any]],
        None,
    ]
    | None,
    event: dict[str, Any],
) -> None:
    if progress_callback is not None:
        progress_callback(
            event
        )


def _case_progress_event(
    case: dict[str, Any],
    event_type: str,
    result: str,
) -> dict[str, Any]:
    return {
        "suite_id": SUITE_ID,
        "event": event_type,
        "case_id": case.get(
            "case_id"
        ),
        "profile_id": case.get(
            "profile_id"
        ),
        "fault_profile": case.get(
            "fault_profile"
        ),
        "operation": case.get(
            "operation"
        ),
        "lba": case.get(
            "lba"
        ),
        "result": result,
    }


def _verify_setup(
    case: dict[str, Any],
    cancellation_token: CancellationToken | None,
) -> dict[str, Any]:
    """
    Use a separate Runner for setup verification
    so the real campaign case still starts CID 1.
    """

    checks: list[
        dict[str, Any]
    ] = []

    _raise_if_cancelled(
        cancellation_token,
        "BEFORE_SETUP",
        checks=checks,
    )

    runner = CommandRunner(
        cancellation_token=(
            cancellation_token
        )
    )

    result = runner.execute(
        "READ",
        lba=case["lba"],
        length=case["length"],
    )

    setup_result = {
        "passed": False,
        "checks": checks,
        "command": result,
    }

    if result.get(
        "aborted",
        False,
    ):
        raise _CaseCancelled(
            stage="SETUP_READ",
            reason=result.get(
                "abort_reason"
            ),
            checks=checks,
            setup=setup_result,
        )

    _add(
        checks,
        "Setup Read Status",
        result["completion"]["status"],
        "SUCCESS",
    )

    data = result[
        "completion"
    ]["data"]

    setup = case[
        "setup"
    ]

    if (
        setup.get("type")
        == "unwritten_lba"
    ):
        _add(
            checks,
            "Setup Unwritten LBA",
            data.get("unwritten"),
            True,
        )

    elif "pattern" in setup:
        _add(
            checks,
            "Setup Pattern",
            data.get("pattern"),
            setup["pattern"],
        )

    else:
        raise ValueError(
            "Unsupported setup definition: "
            f"{setup}"
        )

    setup_result["passed"] = (
        all_checks_passed(
            checks
        )
    )

    return setup_result


def _check_timeout(
    checks: list[dict[str, Any]],
    result: dict[str, Any],
) -> None:

    _add(
        checks,
        "Fault CID",
        result["command"]["cid"],
        1,
    )

    _add(
        checks,
        "Host Timeout Status",
        result["host"]["status"],
        "TIMEOUT",
    )

    _add(
        checks,
        "Timed Out",
        result["timed_out"],
        True,
    )

    _add(
        checks,
        "Timeout Completion",
        result["completion"],
        None,
    )

    _add(
        checks,
        "Timeout Controller Result",
        result["controller_result"],
        None,
    )

    _add(
        checks,
        "Outstanding CID After Timeout",
        result["queue_state"][
            "outstanding_cids"
        ],
        [1],
    )

    _add(
        checks,
        "Next CID After Timeout",
        result["queue_state"][
            "next_cid"
        ],
        2,
    )


def _check_failed_cq(
    checks: list[dict[str, Any]],
    result: dict[str, Any],
    expected_error: str,
) -> None:

    completion = result[
        "completion"
    ]

    _add(
        checks,
        "Fault CID",
        result["command"]["cid"],
        1,
    )

    _add(
        checks,
        "Completion Status",
        completion["status"],
        "FAILED",
    )

    _add(
        checks,
        "Completion Error",
        completion["error"],
        expected_error,
    )

    _add(
        checks,
        "Completion Data",
        completion["data"],
        None,
    )

    _add(
        checks,
        "Timed Out",
        result["timed_out"],
        False,
    )


def _check_log_correlation(
    checks: list[dict[str, Any]],
    result: dict[str, Any],
) -> list[dict[str, Any]]:

    entries = parse_log_file(
        RUNTIME_LOG_FILE
    )

    matches = find_by_cid(
        entries,
        result["command"]["cid"],
    )

    _add(
        checks,
        "Firmware Log CID Count",
        len(matches),
        1,
    )

    if matches:
        entry = matches[0]

        _add(
            checks,
            "Log CID",
            entry["CID"],
            result["command"]["cid"],
        )

        _add(
            checks,
            "Log Opcode",
            entry["Opcode"],
            result["command"]["opcode"],
        )

        _add(
            checks,
            "Log LBA",
            entry["LBA"],
            result["command"]["lba"],
        )

        _add(
            checks,
            "Log Status",
            entry["Status"],
            result["completion"]["status"],
        )

        _add(
            checks,
            "Log Error",
            entry["Error"],
            result["completion"]["error"],
        )

    return entries


def _check_readback(
    checks: list[dict[str, Any]],
    result: dict[str, Any],
    expected: str,
    prefix: str,
) -> None:

    completion = result[
        "completion"
    ]

    data = completion[
        "data"
    ]

    _add(
        checks,
        f"{prefix} Status",
        completion["status"],
        "SUCCESS",
    )

    if expected == "ZERO_BLOCK":

        _add(
            checks,
            f"{prefix} Unwritten",
            data.get("unwritten"),
            True,
        )

        _add(
            checks,
            f"{prefix} LBA",
            data.get("lba"),
            result["command"]["lba"],
        )

    else:

        _add(
            checks,
            f"{prefix} Pattern",
            data.get("pattern"),
            expected,
        )

        _add(
            checks,
            f"{prefix} Unwritten",
            data.get("unwritten"),
            False,
        )


def _run_timeout(
    case: dict[str, Any],
    runner: CommandRunner,
    checks: list[dict[str, Any]],
    cancellation_token: CancellationToken | None,
    setup: dict[str, Any],
) -> dict[str, Any]:
    evidence: dict[
        str,
        Any,
    ] = {}

    kwargs: dict[
        str,
        Any,
    ] = {
        "lba": case["lba"],
        "length": case["length"],
        "fault": "timeout",
    }

    if case["operation"] == "WRITE":
        kwargs["data"] = case[
            "write_pattern"
        ]

    _raise_if_cancelled(
        cancellation_token,
        "BEFORE_FAULT_COMMAND",
        checks=checks,
        setup=setup,
        evidence=evidence,
    )

    before_hash = (
        _storage_hash()
    )

    fault = runner.execute(
        case["operation"],
        **kwargs,
    )

    evidence[
        "fault_command"
    ] = fault

    if fault.get(
        "aborted",
        False,
    ):
        raise _CaseCancelled(
            stage="FAULT_COMMAND",
            reason=fault.get(
                "abort_reason"
            ),
            checks=checks,
            setup=setup,
            evidence=evidence,
        )

    after_hash = (
        _storage_hash()
    )

    _check_timeout(
        checks,
        fault,
    )

    _add(
        checks,
        "Storage Unchanged After Fault",
        after_hash == before_hash,
        True,
    )

    # A real timeout intentionally leaves an outstanding CID.
    # If Stop arrives here, perform cancellation cleanup before
    # leaving the Case. This is distinct from the normal
    # Timeout -> Reset -> Retry validation path.
    if _stop_requested(
        cancellation_token
    ):
        cleanup_reset = (
            runner.reset_controller()
        )

        evidence[
            "abort_cleanup_reset"
        ] = cleanup_reset

        raise _CaseCancelled(
            stage="AFTER_TIMEOUT",
            reason=(
                cancellation_token.reason
                if cancellation_token is not None
                else None
            ),
            checks=checks,
            setup=setup,
            evidence=evidence,
        )

    reset = (
        runner.reset_controller()
    )

    evidence[
        "controller_reset"
    ] = reset

    _add(
        checks,
        "Reset Outstanding CID",
        reset["after"][
            "outstanding_cids"
        ],
        [],
    )

    _add(
        checks,
        "CID Preserved Across Reset",
        reset["after"][
            "next_cid"
        ],
        2,
    )

    if case["operation"] == "READ":
        _raise_if_cancelled(
            cancellation_token,
            "BEFORE_RETRY_READ",
            checks=checks,
            setup=setup,
            evidence=evidence,
        )

        retry = runner.execute(
            "READ",
            lba=case["lba"],
            length=case["length"],
        )

        evidence[
            "retry"
        ] = retry

        if retry.get(
            "aborted",
            False,
        ):
            raise _CaseCancelled(
                stage="RETRY_READ",
                reason=retry.get(
                    "abort_reason"
                ),
                checks=checks,
                setup=setup,
                evidence=evidence,
            )

        _add(
            checks,
            "Retry CID",
            retry["command"]["cid"],
            2,
        )

        _check_readback(
            checks,
            retry,
            case[
                "expected_result"
            ]["readback"],
            "Retry Readback",
        )

        return evidence

    _raise_if_cancelled(
        cancellation_token,
        "BEFORE_RETRY_WRITE",
        checks=checks,
        setup=setup,
        evidence=evidence,
    )

    retry_write = runner.execute(
        "WRITE",
        lba=case["lba"],
        length=case["length"],
        data=case[
            "write_pattern"
        ],
    )

    evidence[
        "retry_write"
    ] = retry_write

    if retry_write.get(
        "aborted",
        False,
    ):
        raise _CaseCancelled(
            stage="RETRY_WRITE",
            reason=retry_write.get(
                "abort_reason"
            ),
            checks=checks,
            setup=setup,
            evidence=evidence,
        )

    _add(
        checks,
        "Retry Write CID",
        retry_write[
            "command"
        ]["cid"],
        2,
    )

    _add(
        checks,
        "Retry Write Status",
        retry_write[
            "completion"
        ]["status"],
        "SUCCESS",
    )

    _raise_if_cancelled(
        cancellation_token,
        "BEFORE_READBACK",
        checks=checks,
        setup=setup,
        evidence=evidence,
    )

    readback = runner.execute(
        "READ",
        lba=case["lba"],
        length=case["length"],
    )

    evidence[
        "readback"
    ] = readback

    if readback.get(
        "aborted",
        False,
    ):
        raise _CaseCancelled(
            stage="READBACK",
            reason=readback.get(
                "abort_reason"
            ),
            checks=checks,
            setup=setup,
            evidence=evidence,
        )

    _add(
        checks,
        "Readback CID",
        readback[
            "command"
        ]["cid"],
        3,
    )

    _check_readback(
        checks,
        readback,
        case[
            "expected_result"
        ]["after_recovery"],
        "Recovery Readback",
    )

    return evidence


def _run_nand_read_fail(
    case: dict[str, Any],
    runner: CommandRunner,
    checks: list[dict[str, Any]],
    cancellation_token: CancellationToken | None,
    setup: dict[str, Any],
) -> dict[str, Any]:
    evidence: dict[
        str,
        Any,
    ] = {}

    _raise_if_cancelled(
        cancellation_token,
        "BEFORE_FAULT_COMMAND",
        checks=checks,
        setup=setup,
        evidence=evidence,
    )

    before_hash = (
        _storage_hash()
    )

    fault = runner.execute(
        "READ",
        lba=case["lba"],
        length=case["length"],
        fault="NAND_READ_FAIL",
    )

    evidence[
        "fault_command"
    ] = fault

    if fault.get(
        "aborted",
        False,
    ):
        raise _CaseCancelled(
            stage="FAULT_COMMAND",
            reason=fault.get(
                "abort_reason"
            ),
            checks=checks,
            setup=setup,
            evidence=evidence,
        )

    after_hash = (
        _storage_hash()
    )

    _check_failed_cq(
        checks,
        fault,
        "NAND_READ_FAIL",
    )

    _raise_if_cancelled(
        cancellation_token,
        "BEFORE_LOG_CORRELATION",
        checks=checks,
        setup=setup,
        evidence=evidence,
    )

    log_entries = (
        _check_log_correlation(
            checks,
            fault,
        )
    )

    evidence[
        "firmware_log_entries"
    ] = log_entries

    _add(
        checks,
        "Storage Unchanged",
        after_hash == before_hash,
        True,
    )

    return evidence


def _run_nand_program_fail(
    case: dict[str, Any],
    runner: CommandRunner,
    checks: list[dict[str, Any]],
    cancellation_token: CancellationToken | None,
    setup: dict[str, Any],
) -> dict[str, Any]:
    evidence: dict[
        str,
        Any,
    ] = {}

    _raise_if_cancelled(
        cancellation_token,
        "BEFORE_FAULT_COMMAND",
        checks=checks,
        setup=setup,
        evidence=evidence,
    )

    before_hash = (
        _storage_hash()
    )

    fault = runner.execute(
        "WRITE",
        lba=case["lba"],
        length=case["length"],
        data=case[
            "write_pattern"
        ],
        fault="NAND_PROGRAM_FAIL",
    )

    evidence[
        "fault_command"
    ] = fault

    if fault.get(
        "aborted",
        False,
    ):
        raise _CaseCancelled(
            stage="FAULT_COMMAND",
            reason=fault.get(
                "abort_reason"
            ),
            checks=checks,
            setup=setup,
            evidence=evidence,
        )

    after_hash = (
        _storage_hash()
    )

    _check_failed_cq(
        checks,
        fault,
        "NAND_PROGRAM_FAIL",
    )

    _raise_if_cancelled(
        cancellation_token,
        "BEFORE_LOG_CORRELATION",
        checks=checks,
        setup=setup,
        evidence=evidence,
    )

    log_entries = (
        _check_log_correlation(
            checks,
            fault,
        )
    )

    evidence[
        "firmware_log_entries"
    ] = log_entries

    _add(
        checks,
        "Storage Unchanged After Fault",
        after_hash == before_hash,
        True,
    )

    _raise_if_cancelled(
        cancellation_token,
        "BEFORE_CONTROLLER_RESET",
        checks=checks,
        setup=setup,
        evidence=evidence,
    )

    reset = (
        runner.reset_controller()
    )

    evidence[
        "controller_reset"
    ] = reset

    _add(
        checks,
        "Reset Outstanding CID",
        reset["after"][
            "outstanding_cids"
        ],
        [],
    )

    _add(
        checks,
        "CID Preserved Across Reset",
        reset["after"][
            "next_cid"
        ],
        2,
    )

    _raise_if_cancelled(
        cancellation_token,
        "BEFORE_RETRY_WRITE",
        checks=checks,
        setup=setup,
        evidence=evidence,
    )

    retry_write = runner.execute(
        "WRITE",
        lba=case["lba"],
        length=case["length"],
        data=case[
            "write_pattern"
        ],
    )

    evidence[
        "retry_write"
    ] = retry_write

    if retry_write.get(
        "aborted",
        False,
    ):
        raise _CaseCancelled(
            stage="RETRY_WRITE",
            reason=retry_write.get(
                "abort_reason"
            ),
            checks=checks,
            setup=setup,
            evidence=evidence,
        )

    _add(
        checks,
        "Retry Write CID",
        retry_write[
            "command"
        ]["cid"],
        2,
    )

    _add(
        checks,
        "Retry Write Status",
        retry_write[
            "completion"
        ]["status"],
        "SUCCESS",
    )

    _raise_if_cancelled(
        cancellation_token,
        "BEFORE_READBACK",
        checks=checks,
        setup=setup,
        evidence=evidence,
    )

    readback = runner.execute(
        "READ",
        lba=case["lba"],
        length=case["length"],
    )

    evidence[
        "readback"
    ] = readback

    if readback.get(
        "aborted",
        False,
    ):
        raise _CaseCancelled(
            stage="READBACK",
            reason=readback.get(
                "abort_reason"
            ),
            checks=checks,
            setup=setup,
            evidence=evidence,
        )

    _add(
        checks,
        "Readback CID",
        readback[
            "command"
        ]["cid"],
        3,
    )

    _check_readback(
        checks,
        readback,
        case[
            "expected_result"
        ]["after_recovery"],
        "Recovery Readback",
    )

    return evidence


def _run_miscompare(
    case: dict[str, Any],
    runner: CommandRunner,
    checks: list[dict[str, Any]],
    cancellation_token: CancellationToken | None,
    setup: dict[str, Any],
) -> dict[str, Any]:
    evidence: dict[
        str,
        Any,
    ] = {}

    _raise_if_cancelled(
        cancellation_token,
        "BEFORE_FAULT_COMMAND",
        checks=checks,
        setup=setup,
        evidence=evidence,
    )

    before_hash = (
        _storage_hash()
    )

    fault = runner.execute(
        "READ",
        lba=case["lba"],
        length=case["length"],
        fault="miscompare",
    )

    evidence[
        "fault_command"
    ] = fault

    if fault.get(
        "aborted",
        False,
    ):
        raise _CaseCancelled(
            stage="FAULT_COMMAND",
            reason=fault.get(
                "abort_reason"
            ),
            checks=checks,
            setup=setup,
            evidence=evidence,
        )

    after_hash = (
        _storage_hash()
    )

    completion = fault[
        "completion"
    ]

    returned_pattern = (
        completion["data"].get(
            "pattern"
        )
    )

    expected_pattern = case[
        "setup"
    ]["pattern"]

    _add(
        checks,
        "Fault CID",
        fault["command"]["cid"],
        1,
    )

    _add(
        checks,
        "CQ Status",
        completion["status"],
        case[
            "expected_result"
        ]["cq_status"],
    )

    _add(
        checks,
        "Injected Response Pattern",
        returned_pattern,
        case[
            "expected_response_pattern"
        ],
    )

    _add(
        checks,
        "Data Miscompare Detected",
        returned_pattern
        != expected_pattern,
        True,
    )

    _add(
        checks,
        "Storage Unchanged After Fault",
        after_hash == before_hash,
        True,
    )

    _raise_if_cancelled(
        cancellation_token,
        "BEFORE_VERIFY_READ",
        checks=checks,
        setup=setup,
        evidence=evidence,
    )

    verify = runner.execute(
        "READ",
        lba=case["lba"],
        length=case["length"],
    )

    evidence[
        "verify_read"
    ] = verify

    if verify.get(
        "aborted",
        False,
    ):
        raise _CaseCancelled(
            stage="VERIFY_READ",
            reason=verify.get(
                "abort_reason"
            ),
            checks=checks,
            setup=setup,
            evidence=evidence,
        )

    _add(
        checks,
        "Verify Read CID",
        verify["command"]["cid"],
        2,
    )

    _add(
        checks,
        "Stored Pattern Preserved",
        verify[
            "completion"
        ]["data"].get(
            "pattern"
        ),
        expected_pattern,
    )

    return evidence


def _case_common_fields(
    case: dict[str, Any],
) -> dict[str, Any]:
    return {
        "case_id": case.get(
            "case_id"
        ),
        "profile_id": case.get(
            "profile_id"
        ),
        "fault_profile": case.get(
            "fault_profile"
        ),
        "operation": case.get(
            "operation"
        ),
        "lba": case.get(
            "lba"
        ),
        "expected_detection": (
            case.get(
                "expected_detection"
            )
        ),
        "recovery": case.get(
            "recovery"
        ),
    }


def _run_case(
    case: dict[str, Any],
    cancellation_token: CancellationToken | None = None,
) -> dict[str, Any]:
    start = time.monotonic()

    setup: dict[
        str,
        Any,
    ] | None = None

    checks: list[
        dict[str, Any]
    ] = []

    evidence: dict[
        str,
        Any,
    ] = {}

    try:
        setup = _verify_setup(
            case,
            cancellation_token,
        )

        checks = list(
            setup["checks"]
        )

        if not setup["passed"]:
            return {
                **_case_common_fields(
                    case
                ),
                "result": "FAIL",
                "duration_sec": (
                    time.monotonic()
                    - start
                ),
                "checks": checks,
                "setup": setup,
                "evidence": None,
                "exception": None,
                "abort": None,
            }

        _raise_if_cancelled(
            cancellation_token,
            "AFTER_SETUP",
            checks=checks,
            setup=setup,
            evidence=evidence,
        )

        # Setup verification created a normal
        # firmware log. Clear it so the actual
        # campaign case owns an isolated log.
        _clear_runtime_log()

        _raise_if_cancelled(
            cancellation_token,
            "BEFORE_FAULT_PHASE",
            checks=checks,
            setup=setup,
            evidence=evidence,
        )

        runner = CommandRunner(
            cancellation_token=(
                cancellation_token
            )
        )

        profile = case[
            "fault_profile"
        ]

        if profile == "timeout":
            evidence = _run_timeout(
                case,
                runner,
                checks,
                cancellation_token,
                setup,
            )

        elif profile == "NAND_READ_FAIL":
            evidence = (
                _run_nand_read_fail(
                    case,
                    runner,
                    checks,
                    cancellation_token,
                    setup,
                )
            )

        elif profile == "NAND_PROGRAM_FAIL":
            evidence = (
                _run_nand_program_fail(
                    case,
                    runner,
                    checks,
                    cancellation_token,
                    setup,
                )
            )

        elif profile == "miscompare":
            evidence = _run_miscompare(
                case,
                runner,
                checks,
                cancellation_token,
                setup,
            )

        else:
            raise ValueError(
                "Unsupported campaign fault "
                f"profile: {profile}"
            )

        return {
            **_case_common_fields(
                case
            ),
            "result": (
                "PASS"
                if all_checks_passed(
                    checks
                )
                else "FAIL"
            ),
            "duration_sec": (
                time.monotonic()
                - start
            ),
            "checks": checks,
            "setup": setup,
            "evidence": evidence,
            "exception": None,
            "abort": None,
        }

    except _CaseCancelled as exc:
        return {
            **_case_common_fields(
                case
            ),
            "result": "ABORTED",
            "duration_sec": (
                time.monotonic()
                - start
            ),
            "checks": list(
                exc.checks
            ),
            "setup": exc.setup,
            "evidence": (
                exc.evidence
                if exc.evidence
                else None
            ),
            "exception": None,
            "abort": {
                "stage": exc.stage,
                "reason": exc.reason,
            },
        }


def _error_case_result(
    case: dict[str, Any],
    exc: Exception,
    duration_sec: float,
) -> dict[str, Any]:
    return {
        **_case_common_fields(
            case
        ),
        "result": "ERROR",
        "duration_sec": duration_sec,
        "checks": [],
        "setup": None,
        "evidence": None,
        "exception": {
            "type": (
                type(exc).__name__
            ),
            "message": str(
                exc
            ),
            "traceback": (
                traceback.format_exc()
            ),
        },
        "abort": None,
    }


def _not_run_case_result(
    case: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    return {
        **_case_common_fields(
            case
        ),
        "result": "NOT_RUN",
        "duration_sec": 0.0,
        "checks": [],
        "setup": None,
        "evidence": None,
        "exception": None,
        "abort": None,
        "not_run_reason": reason,
    }


def _append_not_run_cases(
    case_results: list[dict[str, Any]],
    remaining_cases: list[dict[str, Any]],
    progress_callback: Callable[
        [dict[str, Any]],
        None,
    ]
    | None,
    reason: str,
) -> None:
    for case in remaining_cases:
        result = (
            _not_run_case_result(
                case,
                reason,
            )
        )

        case_results.append(
            result
        )

        _emit_progress(
            progress_callback,
            _case_progress_event(
                case,
                "CASE_NOT_RUN",
                "NOT_RUN",
            ),
        )


def _profile_summary(
    campaign: dict[str, Any],
    case_results: list[dict[str, Any]],
) -> dict[str, dict[str, int]]:
    summary: dict[
        str,
        dict[str, int],
    ] = {}

    for profile_id in campaign[
        "execution_order"
    ]:
        matching = [
            item
            for item in case_results
            if item.get(
                "profile_id"
            )
            == profile_id
        ]

        passed = sum(
            1
            for item in matching
            if item["result"]
            == "PASS"
        )

        failed = sum(
            1
            for item in matching
            if item["result"]
            == "FAIL"
        )

        errors = sum(
            1
            for item in matching
            if item["result"]
            == "ERROR"
        )

        aborted = sum(
            1
            for item in matching
            if item["result"]
            == "ABORTED"
        )

        not_run = sum(
            1
            for item in matching
            if item["result"]
            == "NOT_RUN"
        )

        summary[
            profile_id
        ] = {
            "total": len(
                matching
            ),
            "executed": (
                passed
                + failed
                + errors
                + aborted
            ),
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "aborted": aborted,
            "not_run": not_run,
        }

    return summary


def run(
    cancellation_token: CancellationToken | None = None,
    progress_callback: Callable[
        [dict[str, Any]],
        None,
    ]
    | None = None,
) -> dict[str, Any]:
    start = time.monotonic()

    token = (
        cancellation_token
        if cancellation_token is not None
        else CancellationToken()
    )

    config = (
        load_validation_config()
    )

    campaign = (
        _load_campaign()
    )

    a02_config = config[
        "automation"
    ]["a02"]

    if (
        campaign["suite_id"]
        != SUITE_ID
    ):
        raise ValueError(
            "Campaign suite_id mismatch: "
            f"{campaign['suite_id']}"
        )

    if (
        campaign["execution_order"]
        != a02_config["profile_order"]
    ):
        raise ValueError(
            "A02 profile order mismatch "
            "between validation_config.json "
            "and fault_campaign.json"
        )

    reset_before = bool(
        a02_config.get(
            "reset_storage_before_campaign",
            True,
        )
    )

    reset_after = bool(
        a02_config.get(
            "reset_storage_after_campaign",
            False,
        )
    )

    ordered_cases = (
        _ordered_cases(
            campaign
        )
    )

    case_results: list[
        dict[str, Any]
    ] = []

    stopped = False

    storage_reset_at_start = False
    storage_reset_after_campaign = False

    if _stop_requested(
        token
    ):
        stopped = True

        _append_not_run_cases(
            case_results,
            ordered_cases,
            progress_callback,
            "Not run because campaign stop was requested",
        )

    else:
        if reset_before:
            MockStorage().reset()
            storage_reset_at_start = True

        _clear_runtime_log()

        for index, case in enumerate(
            ordered_cases
        ):
            if _stop_requested(
                token
            ):
                stopped = True

                _append_not_run_cases(
                    case_results,
                    ordered_cases[
                        index:
                    ],
                    progress_callback,
                    "Not run because campaign stop was requested",
                )

                break

            _emit_progress(
                progress_callback,
                _case_progress_event(
                    case,
                    "CASE_STARTED",
                    "STARTED",
                ),
            )

            case_start = (
                time.monotonic()
            )

            try:
                result = _run_case(
                    case,
                    cancellation_token=token,
                )

            except Exception as exc:
                result = (
                    _error_case_result(
                        case,
                        exc,
                        (
                            time.monotonic()
                            - case_start
                        ),
                    )
                )

            case_results.append(
                result
            )

            if result["result"] == "ABORTED":
                event_type = (
                    "CASE_ABORTED"
                )

            elif result["result"] == "ERROR":
                event_type = (
                    "CASE_ERROR"
                )

            else:
                event_type = (
                    "CASE_COMPLETED"
                )

            _emit_progress(
                progress_callback,
                _case_progress_event(
                    case,
                    event_type,
                    result["result"],
                ),
            )

            if result["result"] == "ABORTED":
                stopped = True

                _append_not_run_cases(
                    case_results,
                    ordered_cases[
                        index + 1:
                    ],
                    progress_callback,
                    "Not run because campaign stop was requested",
                )

                break

            # Completion wins:
            # preserve PASS / FAIL / ERROR for this Case.
            # A newly observed Stop only prevents later Cases.
            if (
                index + 1
                < len(
                    ordered_cases
                )
                and _stop_requested(
                    token
                )
            ):
                stopped = True

                _append_not_run_cases(
                    case_results,
                    ordered_cases[
                        index + 1:
                    ],
                    progress_callback,
                    "Not run because campaign stop was requested",
                )

                break

            if (
                result["result"]
                != "PASS"
                and not config[
                    "automation"
                ][
                    "continue_on_case_failure"
                ]
            ):
                break

        if reset_after:
            MockStorage().reset()
            storage_reset_after_campaign = True

    passed = sum(
        1
        for item in case_results
        if item["result"]
        == "PASS"
    )

    failed = sum(
        1
        for item in case_results
        if item["result"]
        == "FAIL"
    )

    errors = sum(
        1
        for item in case_results
        if item["result"]
        == "ERROR"
    )

    aborted = sum(
        1
        for item in case_results
        if item["result"]
        == "ABORTED"
    )

    not_run = sum(
        1
        for item in case_results
        if item["result"]
        == "NOT_RUN"
    )

    executed_cases = (
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
        "suite_name": campaign.get(
            "name",
            SUITE_NAME,
        ),
        "result": suite_result,
        "total_cases": len(
            ordered_cases
        ),
        "executed_cases": (
            executed_cases
        ),
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "aborted": aborted,
        "not_run": not_run,
        "stopped": stopped,
        "stop_reason": stop_reason,
        "duration_sec": (
            time.monotonic()
            - start
        ),
        "storage_reset_at_start": (
            storage_reset_at_start
        ),
        "storage_reset_after_campaign": (
            storage_reset_after_campaign
        ),
        "profile_order": campaign[
            "execution_order"
        ],
        "profile_summary": (
            _profile_summary(
                campaign,
                case_results,
            )
        ),
        "cases": case_results,
    }
