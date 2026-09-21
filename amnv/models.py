from dataclasses import dataclass, field
from typing import Any


@dataclass
class SQEntry:
    cid: int
    opcode: str
    nsid: int = 1
    lba: int | None = None
    length: int | None = None
    data: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "cid": self.cid,
            "opcode": self.opcode,
            "nsid": self.nsid,
            "lba": self.lba,
            "length": self.length,
            "data": self.data,
        }


@dataclass
class CQEntry:
    cid: int
    status: str

    # Logical NVMe SQ Head Pointer returned with completion.
    sq_head: int | None = None

    error: str | None = None
    data: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "cid": self.cid,
            "status": self.status,
            "sq_head": self.sq_head,
            "error": self.error,
            "data": self.data,
        }


TEST_RESULT_STATUSES = frozenset(
    {
        "PASS",
        "FAIL",
        "ERROR",
        "ABORTED",
        "NOT_RUN",
    }
)


@dataclass
class TestResult:
    test_id: str
    test_name: str
    passed: bool

    expected: Any = None
    actual: Any = None

    duration_sec: float = 0.0

    details: dict[str, Any] = field(
        default_factory=dict
    )

    # Optional explicit lifecycle result.
    #
    # Existing Test Cases can keep using only passed=True/False:
    #   True  -> PASS
    #   False -> FAIL
    #
    # STOP v1 can explicitly use:
    #   status="ABORTED"
    #
    # ERROR / NOT_RUN are also supported so the data model
    # matches the suite-level result vocabulary.
    status: str | None = None

    def __post_init__(self) -> None:
        if self.status is None:
            self.status = (
                "PASS"
                if self.passed
                else "FAIL"
            )
        else:
            self.status = (
                self.status
                .strip()
                .upper()
            )

        if self.status not in TEST_RESULT_STATUSES:
            raise ValueError(
                "Unsupported TestResult status: "
                f"{self.status!r}. "
                "Expected one of: "
                f"{sorted(TEST_RESULT_STATUSES)}"
            )

        expected_passed = (
            self.status == "PASS"
        )

        if self.passed != expected_passed:
            raise ValueError(
                "TestResult passed/status mismatch: "
                f"passed={self.passed}, "
                f"status={self.status!r}."
            )

    def result_text(self) -> str:
        return self.status

    def to_dict(self) -> dict[str, Any]:
        return {
            "test_id": self.test_id,
            "test_name": self.test_name,
            "result": self.result_text(),
            "expected": self.expected,
            "actual": self.actual,
            "duration_sec": self.duration_sec,
            "details": self.details,
        }
