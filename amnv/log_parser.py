import re
from pathlib import Path
from typing import Any


LOG_PATTERN = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2} "
    r"\d{2}:\d{2}:\d{2})\s+"
    r"CID=(?P<cid>\d+)\s+"
    r"OPCODE=(?P<opcode>\S+)\s+"
    r"LBA=(?P<lba>\S+)\s+"
    r"STATUS=(?P<status>\S+)\s+"
    r"ERROR=(?P<error>\S+)$"
)


def parse_log_line(
    line: str,
) -> dict[str, Any]:

    match = LOG_PATTERN.match(
        line.strip()
    )

    if match is None:
        raise ValueError(
            f"Invalid firmware log line: {line}"
        )

    values = match.groupdict()

    lba_text = values["lba"]

    return {
        "Timestamp": values["timestamp"],
        "CID": int(values["cid"]),
        "Opcode": values["opcode"],
        "LBA": (
            None
            if lba_text == "-"
            else int(lba_text)
        ),
        "Status": values["status"],
        "Error": values["error"],
    }


def parse_log_file(
    file_path: Path,
) -> list[dict[str, Any]]:

    entries = []

    with file_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        for line_number, line in enumerate(
            file,
            start=1,
        ):
            if not line.strip():
                continue

            try:
                entry = parse_log_line(
                    line
                )

            except ValueError as exc:
                raise ValueError(
                    f"Log parse failed at "
                    f"line {line_number}: {exc}"
                ) from exc

            entries.append(
                entry
            )

    return entries


def find_by_cid(
    entries: list[dict[str, Any]],
    cid: int,
) -> list[dict[str, Any]]:

    return [
        entry
        for entry in entries
        if entry["CID"] == cid
    ]


def find_by_lba(
    entries: list[dict[str, Any]],
    lba: int,
) -> list[dict[str, Any]]:

    return [
        entry
        for entry in entries
        if entry["LBA"] == lba
    ]