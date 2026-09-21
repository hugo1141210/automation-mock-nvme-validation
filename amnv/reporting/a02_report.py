from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    CondPageBreak,
    Flowable,
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from amnv.config_loader import PROJECT_ROOT, load_validation_config


# =========================================================
# Visual Theme
# =========================================================

COLOR_NAVY = HexColor("#0F172A")
COLOR_BLUE = HexColor("#2563EB")
COLOR_BLUE_LIGHT = HexColor("#EFF6FF")

COLOR_GREEN = HexColor("#15803D")
COLOR_GREEN_BG = HexColor("#DCFCE7")

COLOR_RED = HexColor("#B91C1C")
COLOR_RED_BG = HexColor("#FEE2E2")

COLOR_AMBER = HexColor("#B45309")
COLOR_AMBER_BG = HexColor("#FEF3C7")

COLOR_GRAY_50 = HexColor("#F8FAFC")
COLOR_GRAY_100 = HexColor("#F1F5F9")
COLOR_GRAY_200 = HexColor("#E2E8F0")
COLOR_GRAY_500 = HexColor("#64748B")
COLOR_GRAY_700 = HexColor("#334155")

PAGE_WIDTH, PAGE_HEIGHT = A4


# =========================================================
# Styles
# =========================================================

BASE_STYLES = getSampleStyleSheet()

STYLE_TITLE = ParagraphStyle(
    "A02_Title",
    parent=BASE_STYLES["Title"],
    fontName="Helvetica-Bold",
    fontSize=24,
    leading=29,
    textColor=COLOR_NAVY,
    spaceAfter=5 * mm,
)

STYLE_SUBTITLE = ParagraphStyle(
    "A02_Subtitle",
    parent=BASE_STYLES["Normal"],
    fontName="Helvetica",
    fontSize=11,
    leading=15,
    textColor=COLOR_GRAY_500,
    spaceAfter=5 * mm,
)

STYLE_SECTION_NUMBER = ParagraphStyle(
    "A02_SectionNumber",
    parent=BASE_STYLES["Normal"],
    fontName="Helvetica-Bold",
    fontSize=9,
    leading=11,
    textColor=COLOR_BLUE,
    spaceAfter=1 * mm,
)

STYLE_SECTION_TITLE = ParagraphStyle(
    "A02_SectionTitle",
    parent=BASE_STYLES["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=16,
    leading=20,
    textColor=COLOR_NAVY,
    spaceAfter=3 * mm,
)

STYLE_BODY = ParagraphStyle(
    "A02_Body",
    parent=BASE_STYLES["BodyText"],
    fontName="Helvetica",
    fontSize=9,
    leading=13,
    textColor=COLOR_GRAY_700,
)

STYLE_SMALL = ParagraphStyle(
    "A02_Small",
    parent=STYLE_BODY,
    fontSize=8,
    leading=11,
)

STYLE_LABEL = ParagraphStyle(
    "A02_Label",
    parent=STYLE_SMALL,
    fontName="Helvetica-Bold",
    textColor=COLOR_GRAY_500,
)

STYLE_VALUE = ParagraphStyle(
    "A02_Value",
    parent=STYLE_BODY,
    fontName="Helvetica-Bold",
    textColor=COLOR_NAVY,
)

STYLE_TABLE_HEADER = ParagraphStyle(
    "A02_TableHeader",
    parent=STYLE_SMALL,
    fontName="Helvetica-Bold",
    fontSize=7.2,
    leading=9,
    textColor=colors.white,
)

STYLE_TABLE_CELL = ParagraphStyle(
    "A02_TableCell",
    parent=STYLE_SMALL,
    fontSize=7.2,
    leading=9.5,
)

STYLE_TABLE_CELL_BOLD = ParagraphStyle(
    "A02_TableCellBold",
    parent=STYLE_TABLE_CELL,
    fontName="Helvetica-Bold",
    textColor=COLOR_NAVY,
)

STYLE_CARD_TITLE = ParagraphStyle(
    "A02_CardTitle",
    parent=STYLE_BODY,
    fontName="Helvetica-Bold",
    fontSize=10,
    leading=13,
    textColor=COLOR_NAVY,
)

STYLE_MONO = ParagraphStyle(
    "A02_Mono",
    parent=STYLE_SMALL,
    fontName="Courier",
    fontSize=7.2,
    leading=9.5,
    textColor=COLOR_GRAY_700,
)

STYLE_NOTE = ParagraphStyle(
    "A02_Note",
    parent=STYLE_SMALL,
    fontSize=7.5,
    leading=11,
    textColor=COLOR_GRAY_500,
)


# =========================================================
# Campaign Metadata
# =========================================================

PROFILE_LABELS = {
    "FP01": "Command Timeout",
    "FP02": "NAND Read Failure",
    "FP03": "NAND Program Failure",
    "FP04": "Data Miscompare",
}

PROFILE_SUMMARY = {
    "FP01": (
        "Host-side timeout detection followed by Controller Reset "
        "and retry with preserved CID progression."
    ),
    "FP02": (
        "Controller returns FAILED / NAND_READ_FAIL and runtime "
        "firmware log is correlated to the command."
    ),
    "FP03": (
        "Controller returns FAILED / NAND_PROGRAM_FAIL, failed write "
        "does not modify storage, then reset / retry / readback recovers."
    ),
    "FP04": (
        "CQ remains SUCCESS while returned data is corrupted; "
        "the validator detects the mismatch and storage remains intact."
    ),
}


# =========================================================
# Helpers
# =========================================================

def _text(value: Any) -> str:
    if value is None:
        return "None"

    if isinstance(value, bool):
        return "true" if value else "false"

    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(
            _text(item)
            for item in value
        ) + "]"

    return str(value)


def _p(
    value: Any,
    style: ParagraphStyle = STYLE_TABLE_CELL,
) -> Paragraph:
    return Paragraph(
        escape(_text(value)),
        style,
    )


def _safe_get(
    obj: Any,
    *keys: Any,
    default: Any = None,
) -> Any:
    current = obj

    for key in keys:
        if not isinstance(current, dict):
            return default

        if key not in current:
            return default

        current = current[key]

    return current


def _status_colors(
    result: str,
) -> tuple[colors.Color, colors.Color]:
    result = result.upper()

    if result == "PASS":
        return COLOR_GREEN, COLOR_GREEN_BG

    if result in {
        "FAIL",
        "FAILED",
        "ERROR",
    }:
        return COLOR_RED, COLOR_RED_BG

    if result == "NOT_RUN":
        return COLOR_GRAY_500, COLOR_GRAY_100

    # STOPPED / ABORTED and other execution-control
    # states use the amber family.
    return COLOR_AMBER, COLOR_AMBER_BG


def _section_header(
    number: str,
    title: str,
) -> list[Flowable]:
    return [
        Paragraph(
            number,
            STYLE_SECTION_NUMBER,
        ),
        Paragraph(
            title,
            STYLE_SECTION_TITLE,
        ),
        HRFlowable(
            width="100%",
            thickness=0.7,
            color=COLOR_GRAY_200,
            spaceAfter=4 * mm,
        ),
    ]


def _summary_card(
    label: str,
    value: Any,
) -> list[Flowable]:
    return [
        Paragraph(
            escape(_text(value)),
            ParagraphStyle(
                f"A02_CardValue_{label}",
                parent=STYLE_VALUE,
                fontSize=17,
                leading=20,
                alignment=TA_CENTER,
            ),
        ),
        Spacer(
            1,
            1.4 * mm,
        ),
        Paragraph(
            escape(label.upper()),
            ParagraphStyle(
                f"A02_CardLabel_{label}",
                parent=STYLE_SMALL,
                fontSize=7.2,
                leading=9,
                alignment=TA_CENTER,
                textColor=COLOR_GRAY_500,
            ),
        ),
    ]


def _key_value_table(
    rows: list[tuple[str, Any]],
) -> Table:
    data = []

    for key, value in rows:
        data.append(
            [
                Paragraph(
                    escape(key),
                    STYLE_LABEL,
                ),
                Paragraph(
                    escape(_text(value)),
                    STYLE_VALUE,
                ),
            ]
        )

    table = Table(
        data,
        colWidths=[
            45 * mm,
            112 * mm,
        ],
        hAlign="LEFT",
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, -1),
                    COLOR_GRAY_50,
                ),
                (
                    "LINEBELOW",
                    (0, 0),
                    (-1, -1),
                    0.3,
                    COLOR_GRAY_200,
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    3 * mm,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    3 * mm,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    2.1 * mm,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    2.1 * mm,
                ),
            ]
        )
    )

    return table


def _find_filename_pattern(
    obj: Any,
) -> str | None:
    if isinstance(obj, dict):
        if "filename_pattern" in obj:
            return str(
                obj["filename_pattern"]
            )

        for value in obj.values():
            found = _find_filename_pattern(
                value
            )

            if found:
                return found

    return None


def _make_filename(
    suite_id: str,
    generated_at: datetime,
) -> str:
    default_pattern = (
        "{suite_id}_{YYYYMMDD}_{HHMMSS}.pdf"
    )

    try:
        config = load_validation_config()

        pattern = (
            _find_filename_pattern(config)
            or default_pattern
        )

    except Exception:
        pattern = default_pattern

    filename = (
        pattern
        .replace(
            "{suite_id}",
            suite_id,
        )
        .replace(
            "{YYYYMMDD}",
            generated_at.strftime(
                "%Y%m%d"
            ),
        )
        .replace(
            "{HHMMSS}",
            generated_at.strftime(
                "%H%M%S"
            ),
        )
    )

    if not filename.lower().endswith(
        ".pdf"
    ):
        filename += ".pdf"

    return filename


def _checks_summary(
    case: dict[str, Any],
) -> str:
    result = case.get(
        "result",
        "UNKNOWN",
    )

    checks = case.get(
        "checks",
        [],
    )

    if result == "NOT_RUN":
        return "Not executed"

    if (
        result == "ABORTED"
        and not checks
    ):
        return (
            "No completed validation checks"
        )

    passed = sum(
        1
        for check in checks
        if bool(
            check.get(
                "passed"
            )
        )
    )

    return (
        f"{passed} / "
        f"{len(checks)} PASS"
    )


def _case_expected_behavior(
    case: dict[str, Any],
) -> str:
    profile = case.get(
        "profile_id"
    )

    if profile == "FP01":
        if (
            case.get("operation")
            == "WRITE"
        ):
            return (
                "Host TIMEOUT -> Reset -> "
                "Retry WRITE -> Readback"
            )

        return (
            "Host TIMEOUT -> Reset -> "
            "Retry READ"
        )

    if profile == "FP02":
        return (
            "FAILED CQ + NAND_READ_FAIL "
            "+ FW log correlation"
        )

    if profile == "FP03":
        return (
            "FAILED CQ + storage unchanged "
            "+ FW log correlation -> Reset "
            "-> Retry WRITE -> Readback"
        )

    if profile == "FP04":
        return (
            "CQ SUCCESS + data mismatch "
            "detected; storage unchanged"
        )

    return case.get(
        "expected_detection",
        "-",
    )


def _recovery_label(
    case: dict[str, Any],
) -> str:
    recovery = case.get(
        "recovery",
        "",
    )

    mapping = {
        "reset_retry_once":
            "Reset + Retry",
        "reset_retry_once_readback":
            "Reset + Retry + Readback",
        "log_parse_correlation_no_retry":
            "Log correlation / No retry",
        "correlate_reset_retry_once_readback":
            "Correlate + Reset + Retry + Readback",
        "none":
            "None",
    }

    return mapping.get(
        recovery,
        recovery,
    )


# =========================================================
# Header / Footer
# =========================================================

def _draw_header_footer(
    canvas,
    doc,
) -> None:
    canvas.saveState()

    page_number = (
        canvas.getPageNumber()
    )

    if page_number > 1:
        canvas.setStrokeColor(
            COLOR_GRAY_200
        )
        canvas.setLineWidth(
            0.5
        )

        canvas.line(
            doc.leftMargin,
            PAGE_HEIGHT - 14 * mm,
            PAGE_WIDTH - doc.rightMargin,
            PAGE_HEIGHT - 14 * mm,
        )

        canvas.setFont(
            "Helvetica-Bold",
            7.5,
        )
        canvas.setFillColor(
            COLOR_GRAY_500
        )

        canvas.drawString(
            doc.leftMargin,
            PAGE_HEIGHT - 10.5 * mm,
            "Automation Mock NVMe Validation",
        )

    canvas.setStrokeColor(
        COLOR_GRAY_200
    )

    canvas.line(
        doc.leftMargin,
        13 * mm,
        PAGE_WIDTH - doc.rightMargin,
        13 * mm,
    )

    canvas.setFont(
        "Helvetica",
        7,
    )
    canvas.setFillColor(
        COLOR_GRAY_500
    )

    canvas.drawString(
        doc.leftMargin,
        8.5 * mm,
        "Fault Campaign Report",
    )

    canvas.drawRightString(
        PAGE_WIDTH - doc.rightMargin,
        8.5 * mm,
        f"Page {page_number}",
    )

    canvas.restoreState()


# =========================================================
# Cover
# =========================================================

def _build_cover(
    story: list[Flowable],
    suite_result: dict[str, Any],
    generated_at: datetime,
) -> None:
    result = suite_result.get(
        "result",
        "UNKNOWN",
    )

    status_fg, status_bg = (
        _status_colors(result)
    )

    story.append(
        Spacer(
            1,
            16 * mm,
        )
    )

    story.append(
        Paragraph(
            "AUTOMATION MOCK NVMe VALIDATION",
            ParagraphStyle(
                "A02_CoverKicker",
                parent=STYLE_SECTION_NUMBER,
                fontSize=9,
                leading=11,
                textColor=COLOR_BLUE,
                spaceAfter=4 * mm,
            ),
        )
    )

    story.append(
        Paragraph(
            "A02 - Deterministic Fault Campaign",
            STYLE_TITLE,
        )
    )

    story.append(
        Paragraph(
            (
                "Deterministic fault-injection campaign covering "
                "Host timeout, controller-side NAND failures, "
                "data-integrity mismatch detection, firmware-log "
                "correlation, reset, retry, and readback validation."
            ),
            STYLE_SUBTITLE,
        )
    )

    story.append(
        Spacer(
            1,
            5 * mm,
        )
    )

    status_table = Table(
        [
            [
                Paragraph(
                    escape(result),
                    ParagraphStyle(
                        "A02_CoverStatus",
                        parent=STYLE_VALUE,
                        fontSize=23,
                        leading=27,
                        alignment=TA_CENTER,
                        textColor=status_fg,
                    ),
                )
            ]
        ],
        colWidths=[
            55 * mm,
        ],
        rowHeights=[
            18 * mm,
        ],
        hAlign="LEFT",
    )

    status_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    status_bg,
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    1,
                    status_fg,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
            ]
        )
    )

    story.append(
        status_table
    )

    story.append(
        Spacer(
            1,
            10 * mm,
        )
    )

    total_cases = suite_result.get(
        "total_cases",
        0,
    )
    executed_cases = suite_result.get(
        "executed_cases",
        total_cases,
    )

    dashboard = Table(
        [
            [
                _summary_card(
                    "Total",
                    total_cases,
                ),
                _summary_card(
                    "Executed",
                    executed_cases,
                ),
                _summary_card(
                    "Passed",
                    suite_result.get(
                        "passed",
                        0,
                    ),
                ),
                _summary_card(
                    "Failed",
                    suite_result.get(
                        "failed",
                        0,
                    ),
                ),
            ],
            [
                _summary_card(
                    "Error",
                    suite_result.get(
                        "errors",
                        0,
                    ),
                ),
                _summary_card(
                    "Aborted",
                    suite_result.get(
                        "aborted",
                        0,
                    ),
                ),
                _summary_card(
                    "Not Run",
                    suite_result.get(
                        "not_run",
                        0,
                    ),
                ),
                _summary_card(
                    "Duration",
                    (
                        f"{suite_result.get('duration_sec', 0):.3f} s"
                    ),
                ),
            ],
        ],
        colWidths=[
            40 * mm,
            40 * mm,
            40 * mm,
            40 * mm,
        ],
        rowHeights=[
            24 * mm,
            24 * mm,
        ],
        hAlign="LEFT",
    )

    dashboard.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    COLOR_GRAY_50,
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.6,
                    COLOR_GRAY_200,
                ),
                (
                    "INNERGRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    COLOR_GRAY_200,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
            ]
        )
    )

    story.append(
        dashboard
    )

    story.append(
        Spacer(
            1,
            9 * mm,
        )
    )

    active_profiles = sum(
        1
        for value in suite_result.get(
            "profile_summary",
            {},
        ).values()
        if value.get(
            "total",
            0,
        ) > 0
    )

    metadata = [
        (
            "Suite ID",
            suite_result.get(
                "suite_id",
                "A02",
            ),
        ),
        (
            "Suite Name",
            suite_result.get(
                "suite_name",
                (
                    "Automated Fault "
                    "Injection Campaign"
                ),
            ),
        ),
        (
            "Generated",
            generated_at.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        ),
        (
            "Fault Profiles",
            active_profiles,
        ),
        (
            "Storage Reset at Start",
            suite_result.get(
                "storage_reset_at_start",
                False,
            ),
        ),
        (
            "Storage Reset After Campaign",
            suite_result.get(
                "storage_reset_after_campaign",
                False,
            ),
        ),
    ]

    if suite_result.get(
        "stopped",
        False,
    ):
        metadata.extend(
            [
                (
                    "Stop Reason",
                    suite_result.get(
                        "stop_reason",
                        "User requested stop",
                    ),
                ),
                (
                    "Execution State",
                    (
                        f"{executed_cases} executed / "
                        f"{suite_result.get('not_run', 0)} not run"
                    ),
                ),
            ]
        )

    story.append(
        _key_value_table(
            metadata
        )
    )

    story.append(
        PageBreak()
    )


# =========================================================
# Campaign Matrix
# =========================================================

def _build_campaign_matrix(
    story: list[Flowable],
    suite_result: dict[str, Any],
) -> None:
    story.extend(
        _section_header(
            "01",
            "Campaign Matrix",
        )
    )

    rows = [
        [
            _p(
                "Case",
                STYLE_TABLE_HEADER,
            ),
            _p(
                "Fault",
                STYLE_TABLE_HEADER,
            ),
            _p(
                "Cmd",
                STYLE_TABLE_HEADER,
            ),
            _p(
                "LBA",
                STYLE_TABLE_HEADER,
            ),
            _p(
                "Expected Behavior",
                STYLE_TABLE_HEADER,
            ),
            _p(
                "Recovery",
                STYLE_TABLE_HEADER,
            ),
            _p(
                "Result",
                STYLE_TABLE_HEADER,
            ),
        ]
    ]

    for case in suite_result.get(
        "cases",
        [],
    ):
        result = case.get(
            "result",
            "UNKNOWN",
        )

        status_fg, status_bg = (
            _status_colors(result)
        )

        rows.append(
            [
                _p(
                    case.get(
                        "case_id"
                    ),
                    STYLE_TABLE_CELL_BOLD,
                ),
                _p(
                    case.get(
                        "fault_profile"
                    )
                ),
                _p(
                    case.get(
                        "operation"
                    )
                ),
                _p(
                    case.get(
                        "lba"
                    )
                ),
                _p(
                    _case_expected_behavior(
                        case
                    )
                ),
                _p(
                    _recovery_label(
                        case
                    )
                ),
                Paragraph(
                    f"<b>{escape(result)}</b>",
                    ParagraphStyle(
                        (
                            "A02_MatrixResult_"
                            f"{case.get('case_id')}"
                        ),
                        parent=STYLE_TABLE_CELL,
                        alignment=TA_CENTER,
                        textColor=status_fg,
                        backColor=status_bg,
                    ),
                ),
            ]
        )

    table = Table(
        rows,
        colWidths=[
            25 * mm,
            25 * mm,
            15 * mm,
            12 * mm,
            48 * mm,
            33 * mm,
            17 * mm,
        ],
        repeatRows=1,
        hAlign="LEFT",
    )

    commands = [
        (
            "BACKGROUND",
            (0, 0),
            (-1, 0),
            COLOR_NAVY,
        ),
        (
            "GRID",
            (0, 0),
            (-1, -1),
            0.3,
            COLOR_GRAY_200,
        ),
        (
            "VALIGN",
            (0, 0),
            (-1, -1),
            "TOP",
        ),
        (
            "LEFTPADDING",
            (0, 0),
            (-1, -1),
            1.5 * mm,
        ),
        (
            "RIGHTPADDING",
            (0, 0),
            (-1, -1),
            1.5 * mm,
        ),
        (
            "TOPPADDING",
            (0, 0),
            (-1, -1),
            1.7 * mm,
        ),
        (
            "BOTTOMPADDING",
            (0, 0),
            (-1, -1),
            1.7 * mm,
        ),
    ]

    for index in range(
        1,
        len(rows),
    ):
        if index % 2 == 0:
            commands.append(
                (
                    "BACKGROUND",
                    (0, index),
                    (-1, index),
                    COLOR_GRAY_50,
                )
            )

    table.setStyle(
        TableStyle(
            commands
        )
    )

    story.append(
        table
    )

    story.append(
        Spacer(
            1,
            7 * mm,
        )
    )


# =========================================================
# Fault Coverage Summary
# =========================================================

def _build_fault_coverage(
    story: list[Flowable],
    suite_result: dict[str, Any],
) -> None:
    story.extend(
        _section_header(
            "02",
            "Fault Coverage Summary",
        )
    )

    summary = suite_result.get(
        "profile_summary",
        {},
    )

    rows = [
        [
            _p("Profile", STYLE_TABLE_HEADER),
            _p("Fault Type", STYLE_TABLE_HEADER),
            _p("Total", STYLE_TABLE_HEADER),
            _p("Exec", STYLE_TABLE_HEADER),
            _p("Pass", STYLE_TABLE_HEADER),
            _p("Fail", STYLE_TABLE_HEADER),
            _p("Err", STYLE_TABLE_HEADER),
            _p("Abort", STYLE_TABLE_HEADER),
            _p("Not Run", STYLE_TABLE_HEADER),
            _p("Validation Focus", STYLE_TABLE_HEADER),
        ]
    ]

    for profile_id in suite_result.get(
        "profile_order",
        [],
    ):
        item = summary.get(
            profile_id,
            {},
        )

        rows.append(
            [
                _p(
                    profile_id,
                    STYLE_TABLE_CELL_BOLD,
                ),
                _p(
                    PROFILE_LABELS.get(
                        profile_id,
                        profile_id,
                    )
                ),
                _p(
                    item.get(
                        "total",
                        0,
                    )
                ),
                _p(
                    item.get(
                        "executed",
                        item.get(
                            "total",
                            0,
                        ),
                    )
                ),
                _p(
                    item.get(
                        "passed",
                        0,
                    )
                ),
                _p(
                    item.get(
                        "failed",
                        0,
                    )
                ),
                _p(
                    item.get(
                        "errors",
                        0,
                    )
                ),
                _p(
                    item.get(
                        "aborted",
                        0,
                    )
                ),
                _p(
                    item.get(
                        "not_run",
                        0,
                    )
                ),
                _p(
                    PROFILE_SUMMARY.get(
                        profile_id,
                        "-",
                    )
                ),
            ]
        )

    table = Table(
        rows,
        colWidths=[
            15 * mm,
            27 * mm,
            11 * mm,
            11 * mm,
            11 * mm,
            11 * mm,
            11 * mm,
            13 * mm,
            14 * mm,
            50 * mm,
        ],
        hAlign="LEFT",
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    COLOR_GRAY_700,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.3,
                    COLOR_GRAY_200,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    1.4 * mm,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    1.4 * mm,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    1.6 * mm,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    1.6 * mm,
                ),
            ]
        )
    )

    story.append(
        table
    )

    story.append(
        Spacer(
            1,
            7 * mm,
        )
    )


# =========================================================
# Case Evidence
# =========================================================

def _profile_heading(
    profile_id: str,
) -> list[Flowable]:
    return [
        CondPageBreak(
            80 * mm
        ),
        Paragraph(
            (
                f"{escape(profile_id)} - "
                f"{escape(PROFILE_LABELS.get(profile_id, profile_id))}"
            ),
            ParagraphStyle(
                f"A02_Profile_{profile_id}",
                parent=STYLE_SECTION_TITLE,
                fontSize=13,
                leading=16,
                textColor=COLOR_NAVY,
                spaceAfter=2 * mm,
            ),
        ),
        Paragraph(
            escape(
                PROFILE_SUMMARY.get(
                    profile_id,
                    "",
                )
            ),
            STYLE_SMALL,
        ),
        Spacer(
            1,
            4 * mm,
        ),
    ]


def _case_card(
    case: dict[str, Any],
) -> KeepTogether:
    result = case.get(
        "result",
        "UNKNOWN",
    )

    status_fg, status_bg = (
        _status_colors(result)
    )

    title = (
        f"{case.get('case_id')} | "
        f"{case.get('operation')} | "
        f"LBA {case.get('lba')}"
    )

    rows: list[
        tuple[str, Any]
    ] = [
        (
            "Fault",
            case.get(
                "fault_profile"
            ),
        ),
        (
            "Expected Detection",
            case.get(
                "expected_detection"
            ),
        ),
        (
            "Recovery",
            _recovery_label(
                case
            ),
        ),
        (
            "Validation Checks",
            _checks_summary(
                case
            ),
        ),
        (
            "Duration",
            f"{case.get('duration_sec', 0):.3f} s",
        ),
    ]

    # -------------------------------------------------
    # Execution-control states
    # -------------------------------------------------
    if result == "NOT_RUN":
        rows.append(
            (
                "Execution State",
                case.get(
                    "not_run_reason",
                    (
                        "Not run because campaign "
                        "stop was requested"
                    ),
                ),
            )
        )

    elif result == "ABORTED":
        abort = (
            case.get("abort")
            or {}
        )

        rows.extend(
            [
                (
                    "Abort Stage",
                    abort.get(
                        "stage",
                        "UNKNOWN",
                    ),
                ),
                (
                    "Stop Reason",
                    abort.get(
                        "reason",
                        "User requested stop",
                    ),
                ),
            ]
        )

        evidence = (
            case.get("evidence")
            or {}
        )

        fault = evidence.get(
            "fault_command"
        )

        if fault:
            rows.extend(
                [
                    (
                        "Interrupted Command",
                        (
                            f"CID "
                            f"{_safe_get(fault, 'command', 'cid')} / "
                            f"{_safe_get(fault, 'command', 'opcode')} / "
                            f"LBA "
                            f"{_safe_get(fault, 'command', 'lba')}"
                        ),
                    ),
                    (
                        "Host Result",
                        _safe_get(
                            fault,
                            "host",
                            "status",
                        ),
                    ),
                    (
                        "Timed Out",
                        fault.get(
                            "timed_out"
                        ),
                    ),
                ]
            )

            abort_recovery = (
                fault.get(
                    "abort_recovery"
                )
                or {}
            )

            if abort_recovery:
                queue_after = (
                    abort_recovery.get(
                        "queue_after_reset"
                    )
                    or {}
                )

                rows.extend(
                    [
                        (
                            "Process Termination",
                            abort_recovery.get(
                                "termination"
                            ),
                        ),
                        (
                            "Outstanding After Abort",
                            queue_after.get(
                                "outstanding_cids"
                            ),
                        ),
                        (
                            "Queue After Abort",
                            (
                                f"SQ "
                                f"{queue_after.get('sq_head')}/"
                                f"{queue_after.get('sq_tail')}, "
                                f"CQ "
                                f"{queue_after.get('cq_head')}/"
                                f"{queue_after.get('cq_tail')}"
                            ),
                        ),
                        (
                            "Next CID",
                            queue_after.get(
                                "next_cid"
                            ),
                        ),
                    ]
                )

        cleanup_reset = evidence.get(
            "abort_cleanup_reset"
        )

        if cleanup_reset:
            rows.append(
                (
                    "Cancellation Cleanup Reset",
                    (
                        f"Outstanding "
                        f"{_safe_get(cleanup_reset, 'after', 'outstanding_cids')} / "
                        f"next CID "
                        f"{_safe_get(cleanup_reset, 'after', 'next_cid')}"
                    ),
                )
            )

    elif result == "ERROR":
        exception = (
            case.get("exception")
            or {}
        )

        rows.extend(
            [
                (
                    "Exception",
                    exception.get(
                        "type"
                    ),
                ),
                (
                    "Message",
                    exception.get(
                        "message"
                    ),
                ),
            ]
        )

    else:
        # ---------------------------------------------
        # Normal PASS / FAIL evidence
        # ---------------------------------------------
        evidence = (
            case.get("evidence")
            or {}
        )

        profile = case.get(
            "profile_id"
        )

        if profile == "FP01":
            fault = evidence.get(
                "fault_command",
                {},
            )

            reset = evidence.get(
                "controller_reset",
                {},
            )

            rows.extend(
                [
                    (
                        "Fault Result",
                        (
                            f"CID "
                            f"{_safe_get(fault, 'command', 'cid')} / "
                            f"{_safe_get(fault, 'host', 'status')} / "
                            f"Outstanding "
                            f"{_safe_get(fault, 'queue_state', 'outstanding_cids')}"
                        ),
                    ),
                    (
                        "Queue After Timeout",
                        (
                            f"SQ "
                            f"{_safe_get(fault, 'queue_state', 'sq_head')}/"
                            f"{_safe_get(fault, 'queue_state', 'sq_tail')}, "
                            f"CQ "
                            f"{_safe_get(fault, 'queue_state', 'cq_head')}/"
                            f"{_safe_get(fault, 'queue_state', 'cq_tail')}"
                        ),
                    ),
                    (
                        "After Reset",
                        (
                            f"Outstanding "
                            f"{_safe_get(reset, 'after', 'outstanding_cids')} / "
                            f"next CID "
                            f"{_safe_get(reset, 'after', 'next_cid')}"
                        ),
                    ),
                ]
            )

            if "retry" in evidence:
                retry = evidence[
                    "retry"
                ]

                retry_data = (
                    _safe_get(
                        retry,
                        "completion",
                        "data",
                        default={},
                    )
                    or {}
                )

                rows.append(
                    (
                        "Retry READ",
                        (
                            f"CID "
                            f"{_safe_get(retry, 'command', 'cid')} / "
                            f"{_safe_get(retry, 'completion', 'status')} / "
                            f"pattern="
                            f"{retry_data.get('pattern')} / "
                            f"unwritten="
                            f"{retry_data.get('unwritten')}"
                        ),
                    )
                )

            if "retry_write" in evidence:
                retry_write = evidence[
                    "retry_write"
                ]

                readback = evidence[
                    "readback"
                ]

                rows.extend(
                    [
                        (
                            "Retry WRITE",
                            (
                                f"CID "
                                f"{_safe_get(retry_write, 'command', 'cid')} / "
                                f"{_safe_get(retry_write, 'completion', 'status')}"
                            ),
                        ),
                        (
                            "Recovery Readback",
                            (
                                f"CID "
                                f"{_safe_get(readback, 'command', 'cid')} / "
                                f"{_safe_get(readback, 'completion', 'data', 'pattern')}"
                            ),
                        ),
                    ]
                )

        elif profile == "FP02":
            fault = evidence.get(
                "fault_command",
                {},
            )

            logs = evidence.get(
                "firmware_log_entries",
                [],
            )

            log_entry = (
                logs[0]
                if logs
                else {}
            )

            rows.extend(
                [
                    (
                        "CQ Completion",
                        (
                            f"{_safe_get(fault, 'completion', 'status')} / "
                            f"{_safe_get(fault, 'completion', 'error')}"
                        ),
                    ),
                    (
                        "Firmware Log",
                        (
                            f"CID "
                            f"{log_entry.get('CID')} / "
                            f"READ / "
                            f"LBA "
                            f"{log_entry.get('LBA')} / "
                            f"{log_entry.get('Error')}"
                        ),
                    ),
                    (
                        "Correlation",
                        (
                            "CID + Opcode + LBA + "
                            "Status + Error matched"
                        ),
                    ),
                ]
            )

        elif profile == "FP03":
            fault = evidence.get(
                "fault_command",
                {},
            )

            logs = evidence.get(
                "firmware_log_entries",
                [],
            )

            log_entry = (
                logs[0]
                if logs
                else {}
            )

            reset = evidence.get(
                "controller_reset",
                {},
            )

            retry_write = evidence.get(
                "retry_write",
                {},
            )

            readback = evidence.get(
                "readback",
                {},
            )

            rows.extend(
                [
                    (
                        "Fault Completion",
                        (
                            f"{_safe_get(fault, 'completion', 'status')} / "
                            f"{_safe_get(fault, 'completion', 'error')}"
                        ),
                    ),
                    (
                        "Firmware Log",
                        (
                            f"CID "
                            f"{log_entry.get('CID')} / "
                            f"WRITE / "
                            f"LBA "
                            f"{log_entry.get('LBA')} / "
                            f"{log_entry.get('Error')}"
                        ),
                    ),
                    (
                        "After Reset",
                        (
                            f"next CID "
                            f"{_safe_get(reset, 'after', 'next_cid')}"
                        ),
                    ),
                    (
                        "Retry WRITE",
                        (
                            f"CID "
                            f"{_safe_get(retry_write, 'command', 'cid')} / "
                            f"{_safe_get(retry_write, 'completion', 'status')}"
                        ),
                    ),
                    (
                        "Readback",
                        (
                            f"CID "
                            f"{_safe_get(readback, 'command', 'cid')} / "
                            f"{_safe_get(readback, 'completion', 'data', 'pattern')}"
                        ),
                    ),
                ]
            )

        elif profile == "FP04":
            fault = evidence.get(
                "fault_command",
                {},
            )

            verify = evidence.get(
                "verify_read",
                {},
            )

            returned_pattern = (
                _safe_get(
                    fault,
                    "completion",
                    "data",
                    "pattern",
                )
            )

            stored_pattern = (
                _safe_get(
                    verify,
                    "completion",
                    "data",
                    "pattern",
                )
            )

            rows.extend(
                [
                    (
                        "Fault CQ Status",
                        _safe_get(
                            fault,
                            "completion",
                            "status",
                        ),
                    ),
                    (
                        "Returned Pattern",
                        returned_pattern,
                    ),
                    (
                        "Stored Pattern",
                        stored_pattern,
                    ),
                    (
                        "Interpretation",
                        (
                            "CQ completed successfully; "
                            "data validator detected "
                            "returned-data mismatch."
                        ),
                    ),
                ]
            )

    content = [
        [
            Paragraph(
                escape(title),
                STYLE_CARD_TITLE,
            ),
            Paragraph(
                f"<b>{escape(result)}</b>",
                ParagraphStyle(
                    (
                        "A02_CaseResult_"
                        f"{case.get('case_id')}"
                    ),
                    parent=STYLE_SMALL,
                    alignment=TA_CENTER,
                    textColor=status_fg,
                    backColor=status_bg,
                ),
            ),
        ]
    ]

    for key, value in rows:
        content.append(
            [
                Paragraph(
                    escape(key),
                    STYLE_LABEL,
                ),
                Paragraph(
                    escape(
                        _text(value)
                    ),
                    STYLE_MONO,
                ),
            ]
        )

    table = Table(
        content,
        colWidths=[
            47 * mm,
            116 * mm,
        ],
        hAlign="LEFT",
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, 0),
                    COLOR_BLUE_LIGHT,
                ),
                (
                    "BACKGROUND",
                    (1, 0),
                    (1, 0),
                    status_bg,
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.6,
                    COLOR_GRAY_200,
                ),
                (
                    "LINEBELOW",
                    (0, 1),
                    (-1, -1),
                    0.25,
                    COLOR_GRAY_200,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    2.8 * mm,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    2.8 * mm,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    1.7 * mm,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    1.7 * mm,
                ),
            ]
        )
    )

    return KeepTogether(
        [
            table,
            Spacer(
                1,
                4 * mm,
            ),
        ]
    )


def _build_case_evidence(
    story: list[Flowable],
    suite_result: dict[str, Any],
) -> None:
    story.append(
        PageBreak()
    )

    story.extend(
        _section_header(
            "03",
            "Campaign Case Evidence",
        )
    )

    cases = suite_result.get(
        "cases",
        [],
    )

    for profile_id in suite_result.get(
        "profile_order",
        [],
    ):
        profile_cases = [
            case
            for case in cases
            if case.get(
                "profile_id"
            )
            == profile_id
        ]

        if not profile_cases:
            continue

        story.extend(
            _profile_heading(
                profile_id
            )
        )

        for case in profile_cases:
            story.append(
                CondPageBreak(
                    60 * mm
                )
            )

            story.append(
                _case_card(
                    case
                )
            )


# =========================================================
# Campaign Conclusions
# =========================================================

def _build_conclusions(
    story: list[Flowable],
    suite_result: dict[str, Any],
) -> None:
    story.append(
        PageBreak()
    )

    story.extend(
        _section_header(
            "04",
            "Campaign Conclusions",
        )
    )

    cases = suite_result.get(
        "cases",
        [],
    )

    result = suite_result.get(
        "result",
        "UNKNOWN",
    )

    if result == "STOPPED":
        aborted_ids = [
            case.get(
                "case_id"
            )
            for case in cases
            if case.get(
                "result"
            )
            == "ABORTED"
        ]

        conclusions = [
            (
                "Campaign Result",
                "STOPPED",
            ),
            (
                "Stop Reason",
                suite_result.get(
                    "stop_reason",
                    "User requested stop",
                ),
            ),
            (
                "Execution State",
                (
                    f"{suite_result.get('executed_cases', 0)} / "
                    f"{suite_result.get('total_cases', 0)} cases executed"
                ),
            ),
            (
                "Aborted Cases",
                (
                    ", ".join(
                        item
                        for item in aborted_ids
                        if item
                    )
                    or "None"
                ),
            ),
            (
                "Not Run",
                suite_result.get(
                    "not_run",
                    0,
                ),
            ),
            (
                "Interpretation",
                (
                    "The active Case was cooperatively cancelled "
                    "when applicable; remaining scheduled Cases "
                    "were not started and are not treated as failures."
                ),
            ),
        ]

    else:
        all_passed = (
            bool(cases)
            and all(
                case.get(
                    "result"
                )
                == "PASS"
                for case in cases
            )
        )

        conclusions = [
            (
                "Host Detection",
                (
                    "Timeout faults are detected by "
                    "the Host without a normal CQ completion."
                ),
            ),
            (
                "Controller Error Detection",
                (
                    "NAND_READ_FAIL and NAND_PROGRAM_FAIL "
                    "surface as deterministic FAILED completions."
                ),
            ),
            (
                "Firmware Log Correlation",
                (
                    "Controller-side NAND failures are correlated "
                    "by CID, opcode, LBA, status, and error."
                ),
            ),
            (
                "Data Integrity Validation",
                (
                    "Miscompare cases preserve CQ SUCCESS while "
                    "the validator detects returned-data mismatch."
                ),
            ),
            (
                "Recovery",
                (
                    "Controller Reset clears queue/outstanding state, "
                    "preserves CID progression, and recovery uses "
                    "a new CID."
                ),
            ),
            (
                "Data Protection",
                (
                    "Failed or timed-out WRITE paths do not modify "
                    "storage before successful retry."
                ),
            ),
            (
                "Campaign Result",
                (
                    "All configured deterministic fault cases passed."
                    if all_passed
                    else (
                        "One or more executed deterministic "
                        "fault cases did not pass."
                    )
                ),
            ),
        ]

    story.append(
        _key_value_table(
            conclusions
        )
    )

    story.append(
        Spacer(
            1,
            7 * mm,
        )
    )

    story.append(
        Paragraph(
            (
                "<b>STOP v1:</b> Cancellation is cooperative. "
                "Active fake_nvme subprocesses can be terminated "
                "and recovered through simulated controller reset; "
                "arbitrary Python deadlocks or non-cooperative "
                "infinite loops are outside the v1 stop guarantee."
            ),
            STYLE_NOTE,
        )
    )

    story.append(
        Spacer(
            1,
            3 * mm,
        )
    )

    story.append(
        Paragraph(
            (
                "<b>Scope:</b> This is a deterministic Host-side "
                "logical NVMe validation campaign. It demonstrates "
                "automation, fault detection, recovery reasoning, "
                "firmware-log correlation, and data-integrity "
                "validation. It does not claim physical SSD firmware "
                "or PCIe hardware validation."
            ),
            STYLE_NOTE,
        )
    )


# =========================================================
# Public API
# =========================================================

def generate_a02_report(
    suite_result: dict[str, Any],
    output_dir: Path | None = None,
) -> Path:
    generated_at = (
        datetime.now()
    )

    suite_id = suite_result.get(
        "suite_id",
        "A02",
    )

    if output_dir is None:
        output_dir = (
            PROJECT_ROOT
            / "reports"
            / suite_id
        )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        output_dir
        / _make_filename(
            suite_id,
            generated_at,
        )
    )

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=17 * mm,
        leftMargin=17 * mm,
        topMargin=20 * mm,
        bottomMargin=18 * mm,
        title=(
            "A02 Fault Campaign Report"
        ),
        author=(
            "Automation Mock NVMe Validation"
        ),
        subject=(
            "Deterministic NVMe fault "
            "injection campaign report"
        ),
    )

    story: list[Flowable] = []

    _build_cover(
        story,
        suite_result,
        generated_at,
    )

    _build_campaign_matrix(
        story,
        suite_result,
    )

    _build_fault_coverage(
        story,
        suite_result,
    )

    _build_case_evidence(
        story,
        suite_result,
    )

    _build_conclusions(
        story,
        suite_result,
    )

    doc.build(
        story,
        onFirstPage=(
            _draw_header_footer
        ),
        onLaterPages=(
            _draw_header_footer
        ),
    )

    return output_path
