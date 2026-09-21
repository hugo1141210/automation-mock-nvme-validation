from typing import Any


def check_equal(
    name: str,
    actual: Any,
    expected: Any,
) -> dict[str, Any]:

    return {
        "name": name,
        "passed": actual == expected,
        "expected": expected,
        "actual": actual,
    }


def check_not_equal(
    name: str,
    actual: Any,
    expected: Any,
) -> dict[str, Any]:

    return {
        "name": name,
        "passed": actual != expected,
        "expected": f"!= {expected}",
        "actual": actual,
    }


def check_maximum(
    name: str,
    actual: int | float,
    maximum: int | float,
) -> dict[str, Any]:

    return {
        "name": name,
        "passed": actual <= maximum,
        "expected": f"<= {maximum}",
        "actual": actual,
    }


def check_completion_status(
    command_result: dict[str, Any],
    expected_status: str,
) -> dict[str, Any]:

    completion = command_result.get(
        "completion"
    )

    actual_status = (
        completion.get("status")
        if completion is not None
        else None
    )

    return {
        "name": "Completion Status",
        "passed": (
            actual_status == expected_status
        ),
        "expected": expected_status,
        "actual": actual_status,
    }


def all_checks_passed(
    checks: list[dict[str, Any]],
) -> bool:

    return all(
        check["passed"]
        for check in checks
    )