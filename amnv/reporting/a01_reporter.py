from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT
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
COLOR_GRAY_400 = HexColor("#94A3B8")
COLOR_GRAY_500 = HexColor("#64748B")
COLOR_GRAY_700 = HexColor("#334155")
COLOR_GRAY_900 = HexColor("#0F172A")

PAGE_WIDTH, PAGE_HEIGHT = A4


# =========================================================
# Styles
# =========================================================

BASE_STYLES = getSampleStyleSheet()

STYLE_TITLE = ParagraphStyle(
    "AMNV_Title",
    parent=BASE_STYLES["Title"],
    fontName="Helvetica-Bold",
    fontSize=24,
    leading=29,
    textColor=COLOR_NAVY,
    spaceAfter=5 * mm,
)

STYLE_SUBTITLE = ParagraphStyle(
    "AMNV_Subtitle",
    parent=BASE_STYLES["Normal"],
    fontName="Helvetica",
    fontSize=11,
    leading=15,
    textColor=COLOR_GRAY_500,
    spaceAfter=5 * mm,
)

STYLE_SECTION_NUMBER = ParagraphStyle(
    "AMNV_SectionNumber",
    parent=BASE_STYLES["Normal"],
    fontName="Helvetica-Bold",
    fontSize=9,
    leading=11,
    textColor=COLOR_BLUE,
    spaceAfter=1 * mm,
)

STYLE_SECTION_TITLE = ParagraphStyle(
    "AMNV_SectionTitle",
    parent=BASE_STYLES["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=16,
    leading=20,
    textColor=COLOR_NAVY,
    spaceAfter=3 * mm,
)

STYLE_BODY = ParagraphStyle(
    "AMNV_Body",
    parent=BASE_STYLES["BodyText"],
    fontName="Helvetica",
    fontSize=9,
    leading=13,
    textColor=COLOR_GRAY_700,
)

STYLE_BODY_SMALL = ParagraphStyle(
    "AMNV_BodySmall",
    parent=STYLE_BODY,
    fontSize=8,
    leading=11,
)

STYLE_LABEL = ParagraphStyle(
    "AMNV_Label",
    parent=STYLE_BODY_SMALL,
    fontName="Helvetica-Bold",
    textColor=COLOR_GRAY_500,
)

STYLE_VALUE = ParagraphStyle(
    "AMNV_Value",
    parent=STYLE_BODY,
    fontName="Helvetica-Bold",
    textColor=COLOR_NAVY,
)

STYLE_CARD_VALUE = ParagraphStyle(
    "AMNV_CardValue",
    parent=STYLE_VALUE,
    fontSize=17,
    leading=20,
    alignment=TA_CENTER,
)

STYLE_CARD_LABEL = ParagraphStyle(
    "AMNV_CardLabel",
    parent=STYLE_BODY_SMALL,
    fontSize=7.5,
    leading=10,
    alignment=TA_CENTER,
    textColor=COLOR_GRAY_500,
)

STYLE_TABLE_HEADER = ParagraphStyle(
    "AMNV_TableHeader",
    parent=STYLE_BODY_SMALL,
    fontName="Helvetica-Bold",
    fontSize=7.5,
    leading=9,
    textColor=colors.white,
)

STYLE_TABLE_CELL = ParagraphStyle(
    "AMNV_TableCell",
    parent=STYLE_BODY_SMALL,
    fontSize=7.5,
    leading=10,
)

STYLE_TABLE_CELL_BOLD = ParagraphStyle(
    "AMNV_TableCellBold",
    parent=STYLE_TABLE_CELL,
    fontName="Helvetica-Bold",
    textColor=COLOR_NAVY,
)

STYLE_NOTE = ParagraphStyle(
    "AMNV_Note",
    parent=STYLE_BODY_SMALL,
    fontSize=7.5,
    leading=11,
    textColor=COLOR_GRAY_500,
)

STYLE_EVIDENCE_TITLE = ParagraphStyle(
    "AMNV_EvidenceTitle",
    parent=STYLE_BODY,
    fontName="Helvetica-Bold",
    fontSize=10,
    leading=13,
    textColor=COLOR_NAVY,
)

STYLE_MONO = ParagraphStyle(
    "AMNV_Mono",
    parent=STYLE_BODY_SMALL,
    fontName="Courier",
    fontSize=7.4,
    leading=10,
    textColor=COLOR_GRAY_700,
)


# =========================================================
# Compact-detail configuration (v3 smart pagination)
# =========================================================

# Detailed Results intentionally shows only the most useful checks.
# Full raw checks still remain in the Suite result / console data.
KEY_CHECK_NAMES: dict[str, list[str]] = {
    "T01": [
        "Firmware Revision",
        "Capacity Blocks",
        "Logical Block Size",
        "Temperature",
        "Critical Warning",
        "Media Errors",
    ],
    "T02": [
        "Completion Status",
        "Readback LBA",
        "Readback Length",
        "Readback Data",
        "Unwritten Flag",
    ],
    "T03": [
        "Completion Status",
        "Completion Error",
        "Completion Data",
        "Timed Out",
    ],
    "T04": [
        "Completion Status",
        "Completion Error",
        "Completion Data",
        "Timed Out",
        "Submitted Opcode",
    ],
    "T05": [
        "Host Timeout Status",
        "Outstanding CID After Timeout",
        "SQ State After Timeout",
        "CQ State After Timeout",
        "CID Preserved Across Reset",
        "Retry CID",
        "Retry Readback Data",
        "Final Next CID",
    ],
    "T06": [
        "Fault Read LBA",
        "Data Miscompare Detection",
        "Stored Data Preserved",
        "Stored Data LBA",
    ],
    "T07": [
        "Parsed Entry Count",
        "Required Fields Present",
        "CID 5 Opcode",
        "CID 5 LBA",
        "CID 5 Error",
        "LBA 2000 Error",
    ],
    "T08": [
        "Completion Status",
        "Completion Error",
        "CID Correlation Count",
        "LBA Correlation Count",
        "Log CID",
        "Log LBA",
        "Log Error",
    ],
    "T09": [
        "Program Failure Error",
        "Storage Unchanged",
        "CID Preserved Across Reset",
        "Retry Write CID",
        "Readback CID",
        "Recovered Data",
        "Final SQ State",
        "Final CQ State",
        "Final Next CID",
    ],
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
        return "[" + ", ".join(_text(item) for item in value) + "]"

    return str(value)


def _paragraph(
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


def _find_filename_pattern(obj: Any) -> str | None:
    if isinstance(obj, dict):
        if "filename_pattern" in obj:
            return str(obj["filename_pattern"])

        for value in obj.values():
            found = _find_filename_pattern(value)
            if found:
                return found

    return None


def _make_filename(
    suite_id: str,
    generated_at: datetime,
) -> str:
    default_pattern = "{suite_id}_{YYYYMMDD}_{HHMMSS}.pdf"

    try:
        config = load_validation_config()
        pattern = _find_filename_pattern(config) or default_pattern
    except Exception:
        pattern = default_pattern

    filename = (
        pattern
        .replace("{suite_id}", suite_id)
        .replace("{YYYYMMDD}", generated_at.strftime("%Y%m%d"))
        .replace("{HHMMSS}", generated_at.strftime("%H%M%S"))
    )

    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"

    return filename


def _status_colors(
    result: str,
) -> tuple[colors.Color, colors.Color]:
    result = result.upper()

    if result == "PASS":
        return COLOR_GREEN, COLOR_GREEN_BG

    if result in {"FAIL", "FAILED", "ERROR"}:
        return COLOR_RED, COLOR_RED_BG

    if result in {"STOPPED", "ABORTED"}:
        return COLOR_AMBER, COLOR_AMBER_BG

    if result == "NOT_RUN":
        return COLOR_GRAY_500, COLOR_GRAY_100

    return COLOR_AMBER, COLOR_AMBER_BG


def _section_header(
    number: str,
    title: str,
) -> list[Flowable]:
    return [
        Paragraph(number, STYLE_SECTION_NUMBER),
        Paragraph(title, STYLE_SECTION_TITLE),
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
            STYLE_CARD_VALUE,
        ),
        Spacer(1, 1.5 * mm),
        Paragraph(
            escape(label.upper()),
            STYLE_CARD_LABEL,
        ),
    ]


def _key_value_table(
    rows: list[tuple[str, Any]],
) -> Table:
    data = []

    for key, value in rows:
        data.append(
            [
                Paragraph(escape(key), STYLE_LABEL),
                Paragraph(escape(_text(value)), STYLE_VALUE),
            ]
        )

    table = Table(
        data,
        colWidths=[42 * mm, 115 * mm],
        hAlign="LEFT",
    )

    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (0, -1), COLOR_GRAY_50),
                ("LINEBELOW", (0, 0), (-1, -1), 0.3, COLOR_GRAY_200),
                ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 2.1 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.1 * mm),
            ]
        )
    )

    return table


def _find_test(
    suite_result: dict[str, Any],
    test_id: str,
) -> dict[str, Any] | None:
    for test in suite_result.get("tests", []):
        if test.get("test_id") == test_id:
            return test

    return None


def _get_checks(test: dict[str, Any]) -> list[dict[str, Any]]:
    detail = test.get("details") or {}

    return _safe_get(
        detail,
        "details",
        "checks",
        default=[],
    ) or []


def _select_key_checks(
    test_id: str,
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    wanted = KEY_CHECK_NAMES.get(test_id)

    if not wanted:
        return checks[:6]

    selected: list[dict[str, Any]] = []

    # Preserve the configured display order.
    for name in wanted:
        for check in checks:
            if check.get("name") == name:
                selected.append(check)
                break

    return selected


def _checks_summary(
    checks: list[dict[str, Any]],
    result: str = "UNKNOWN",
) -> str:
    passed = sum(
        1
        for check in checks
        if bool(check.get("passed"))
    )

    result = result.upper()

    if result == "NOT_RUN":
        return "Not executed"

    if result == "ABORTED":
        if not checks:
            return "No completed validation checks"

        return (
            f"{passed} / {len(checks)} PASS "
            "before abort"
        )

    if result == "ERROR":
        if not checks:
            return "No completed validation checks"

        return (
            f"{passed} / {len(checks)} PASS "
            "before error"
        )

    return f"{passed} / {len(checks)} PASS"


# =========================================================
# Page Header / Footer
# =========================================================

def _draw_header_footer(canvas, doc) -> None:
    canvas.saveState()

    page_number = canvas.getPageNumber()

    if page_number > 1:
        canvas.setStrokeColor(COLOR_GRAY_200)
        canvas.setLineWidth(0.5)

        canvas.line(
            doc.leftMargin,
            PAGE_HEIGHT - 14 * mm,
            PAGE_WIDTH - doc.rightMargin,
            PAGE_HEIGHT - 14 * mm,
        )

        canvas.setFont("Helvetica-Bold", 7.5)
        canvas.setFillColor(COLOR_GRAY_500)

        canvas.drawString(
            doc.leftMargin,
            PAGE_HEIGHT - 10.5 * mm,
            "Automation Mock NVMe Validation",
        )

    canvas.setStrokeColor(COLOR_GRAY_200)

    canvas.line(
        doc.leftMargin,
        13 * mm,
        PAGE_WIDTH - doc.rightMargin,
        13 * mm,
    )

    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(COLOR_GRAY_500)

    canvas.drawString(
        doc.leftMargin,
        8.5 * mm,
        "Validation Report",
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
    suite_id = suite_result.get("suite_id", "UNKNOWN")
    suite_name = suite_result.get("suite_name", "Validation Suite")
    result = suite_result.get("result", "UNKNOWN")

    status_fg, status_bg = _status_colors(result)

    story.append(Spacer(1, 16 * mm))

    story.append(
        Paragraph(
            "AUTOMATION MOCK NVMe VALIDATION",
            ParagraphStyle(
                "CoverKicker",
                parent=STYLE_SECTION_NUMBER,
                fontSize=9,
                leading=11,
                textColor=COLOR_BLUE,
                alignment=TA_LEFT,
                spaceAfter=4 * mm,
            ),
        )
    )

    story.append(
        Paragraph(
            f"{escape(suite_id)} - {escape(suite_name)}",
            STYLE_TITLE,
        )
    )

    story.append(
        Paragraph(
            "Host-side logical NVMe validation framework "
            "with deterministic fault injection, queue lifecycle "
            "tracking, recovery validation, and firmware-log correlation.",
            STYLE_SUBTITLE,
        )
    )

    story.append(Spacer(1, 4 * mm))

    status_table = Table(
        [
            [
                Paragraph(
                    escape(result),
                    ParagraphStyle(
                        "CoverStatus",
                        parent=STYLE_VALUE,
                        fontSize=23,
                        leading=27,
                        alignment=TA_CENTER,
                        textColor=status_fg,
                    ),
                )
            ]
        ],
        colWidths=[55 * mm],
        rowHeights=[18 * mm],
        hAlign="LEFT",
    )

    status_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), status_bg),
                ("BOX", (0, 0), (-1, -1), 1, status_fg),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )

    story.append(status_table)
    story.append(Spacer(1, 12 * mm))

    summary_table = Table(
        [
            [
                _summary_card(
                    "Total",
                    suite_result.get("total_tests", 0),
                ),
                _summary_card(
                    "Executed",
                    suite_result.get("executed", 0),
                ),
                _summary_card(
                    "Passed",
                    suite_result.get("passed", 0),
                ),
                _summary_card(
                    "Failed",
                    suite_result.get("failed", 0),
                ),
            ],
            [
                _summary_card(
                    "Error",
                    suite_result.get("errors", 0),
                ),
                _summary_card(
                    "Aborted",
                    suite_result.get("aborted", 0),
                ),
                _summary_card(
                    "Not Run",
                    suite_result.get("not_run", 0),
                ),
                _summary_card(
                    "Duration",
                    f"{suite_result.get('duration_sec', 0):.3f} s",
                ),
            ],
        ],
        colWidths=[40 * mm, 40 * mm, 40 * mm, 40 * mm],
        rowHeights=[23 * mm, 23 * mm],
        hAlign="LEFT",
    )

    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), COLOR_GRAY_50),
                ("BOX", (0, 0), (-1, -1), 0.6, COLOR_GRAY_200),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, COLOR_GRAY_200),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
            ]
        )
    )

    story.append(summary_table)
    story.append(Spacer(1, 9 * mm))

    metadata_rows: list[tuple[str, Any]] = [
        ("Suite ID", suite_id),
        ("Suite Name", suite_name),
        (
            "Generated",
            generated_at.strftime("%Y-%m-%d %H:%M:%S"),
        ),
        (
            "Storage Baseline Reset",
            suite_result.get("storage_reset_at_start", False),
        ),
    ]

    if result.upper() == "STOPPED":
        metadata_rows.extend(
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
                        f"{suite_result.get('executed', 0)} executed / "
                        f"{suite_result.get('not_run', 0)} not run"
                    ),
                ),
            ]
        )

    story.append(
        _key_value_table(
            metadata_rows
        )
    )

    story.append(PageBreak())


# =========================================================
# Test Summary
# =========================================================

def _build_test_summary(
    story: list[Flowable],
    suite_result: dict[str, Any],
) -> None:
    story.extend(_section_header("01", "Test Summary"))

    rows = [
        [
            _paragraph("ID", STYLE_TABLE_HEADER),
            _paragraph("Test", STYLE_TABLE_HEADER),
            _paragraph("Result", STYLE_TABLE_HEADER),
            _paragraph("Duration", STYLE_TABLE_HEADER),
        ]
    ]

    for test in suite_result.get("tests", []):
        detail = test.get("details") or {}

        test_name = detail.get(
            "test_name",
            test.get("test_id", ""),
        )

        result = test.get("result", "UNKNOWN")
        result_fg, result_bg = _status_colors(result)

        rows.append(
            [
                _paragraph(
                    test.get("test_id", ""),
                    STYLE_TABLE_CELL_BOLD,
                ),
                _paragraph(test_name),
                Paragraph(
                    f"<b>{escape(result)}</b>",
                    ParagraphStyle(
                        f"SummaryResult_{result}",
                        parent=STYLE_TABLE_CELL,
                        alignment=TA_CENTER,
                        textColor=result_fg,
                        backColor=result_bg,
                    ),
                ),
                _paragraph(
                    f"{test.get('duration_sec', 0):.3f} s"
                ),
            ]
        )

    table = Table(
        rows,
        colWidths=[18 * mm, 91 * mm, 27 * mm, 27 * mm],
        repeatRows=1,
        hAlign="LEFT",
    )

    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_NAVY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.35, COLOR_GRAY_200),
        ("LEFTPADDING", (0, 0), (-1, -1), 2.5 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2.5 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 2.1 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.1 * mm),
    ]

    for row_index in range(1, len(rows)):
        if row_index % 2 == 0:
            commands.append(
                (
                    "BACKGROUND",
                    (0, row_index),
                    (-1, row_index),
                    COLOR_GRAY_50,
                )
            )

    table.setStyle(TableStyle(commands))

    story.append(table)
    story.append(Spacer(1, 7 * mm))


# =========================================================
# Compact Detailed Results
# =========================================================

def _build_compact_test_block(
    test: dict[str, Any],
) -> KeepTogether:
    detail = test.get("details") or {}

    test_id = test.get("test_id", "UNKNOWN")
    test_name = detail.get("test_name", test_id)
    result = test.get("result", "UNKNOWN")

    result_fg, result_bg = _status_colors(result)

    checks = _get_checks(test)
    key_checks = _select_key_checks(test_id, checks)

    heading = Table(
        [
            [
                Paragraph(
                    f"<b>{escape(test_id)}</b>",
                    ParagraphStyle(
                        f"{test_id}_id",
                        parent=STYLE_SECTION_TITLE,
                        fontSize=11.5,
                        leading=14,
                        textColor=COLOR_BLUE,
                    ),
                ),
                Paragraph(
                    escape(test_name),
                    ParagraphStyle(
                        f"{test_id}_name",
                        parent=STYLE_SECTION_TITLE,
                        fontSize=11.5,
                        leading=14,
                    ),
                ),
                Paragraph(
                    f"<b>{escape(result)}</b>",
                    ParagraphStyle(
                        f"{test_id}_result",
                        parent=STYLE_BODY,
                        fontName="Helvetica-Bold",
                        fontSize=8,
                        leading=10,
                        alignment=TA_CENTER,
                        textColor=result_fg,
                        backColor=result_bg,
                    ),
                ),
            ]
        ],
        colWidths=[17 * mm, 119 * mm, 27 * mm],
    )

    heading.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LINEBELOW", (0, 0), (-1, -1), 0.7, COLOR_GRAY_200),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2 * mm),
            ]
        )
    )

    block: list[Flowable] = [
        heading,
        Spacer(1, 2.5 * mm),
    ]

    exception = test.get("exception")

    if exception:
        block.append(
            _key_value_table(
                [
                    ("Exception", exception.get("type")),
                    ("Message", exception.get("message")),
                ]
            )
        )
        block.append(Spacer(1, 5 * mm))
        return KeepTogether(block)

    detail_rows: list[tuple[str, Any]] = [
        ("Expected", detail.get("expected", "-")),
        ("Actual", detail.get("actual", "-")),
        (
            "Validation Checks",
            _checks_summary(
                checks,
                result,
            ),
        ),
        (
            "Duration",
            f"{test.get('duration_sec', 0):.3f} s",
        ),
    ]

    abort_info = _safe_get(
        detail,
        "details",
        "abort",
        default={},
    )

    if result.upper() == "ABORTED":
        detail_rows.extend(
            [
                (
                    "Abort Stage",
                    abort_info.get("stage", "-"),
                ),
                (
                    "Stop Reason",
                    abort_info.get("reason", "-"),
                ),
            ]
        )

    block.append(
        _key_value_table(
            detail_rows
        )
    )

    block.append(Spacer(1, 3 * mm))

    if key_checks:
        rows = [
            [
                _paragraph("Key Validation", STYLE_TABLE_HEADER),
                _paragraph("Expected", STYLE_TABLE_HEADER),
                _paragraph("Actual", STYLE_TABLE_HEADER),
                _paragraph("Status", STYLE_TABLE_HEADER),
            ]
        ]

        for check in key_checks:
            passed = bool(check.get("passed", False))
            status = "PASS" if passed else "FAIL"
            status_fg, status_bg = _status_colors(status)

            rows.append(
                [
                    _paragraph(
                        check.get("name", ""),
                        STYLE_TABLE_CELL_BOLD,
                    ),
                    _paragraph(check.get("expected", "")),
                    _paragraph(check.get("actual", "")),
                    Paragraph(
                        f"<b>{status}</b>",
                        ParagraphStyle(
                            f"{test_id}_{status}",
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
            colWidths=[58 * mm, 42 * mm, 42 * mm, 21 * mm],
            repeatRows=1,
            hAlign="LEFT",
        )

        commands = [
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_GRAY_700),
            ("GRID", (0, 0), (-1, -1), 0.3, COLOR_GRAY_200),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 2 * mm),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2 * mm),
            ("TOPPADDING", (0, 0), (-1, -1), 1.55 * mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1.55 * mm),
        ]

        for index in range(1, len(rows)):
            if index % 2 == 0:
                commands.append(
                    (
                        "BACKGROUND",
                        (0, index),
                        (-1, index),
                        COLOR_GRAY_50,
                    )
                )

        table.setStyle(TableStyle(commands))
        block.append(table)

    block.append(Spacer(1, 5 * mm))

    return KeepTogether(block)


def _build_detailed_results(
    story: list[Flowable],
    suite_result: dict[str, Any],
) -> None:
    story.extend(
        _section_header(
            "02",
            "Detailed Validation Results",
        )
    )

    tests = suite_result.get("tests", [])

    # v3:
    # Do not force specific Txx groups onto fixed pages.
    # Keep each compact test block intact, and only request
    # a new page when the remaining space is too small to
    # start another useful block.
    for index, test in enumerate(tests):
        if index > 0:
            story.append(
                CondPageBreak(
                    74 * mm
                )
            )

        story.append(
            _build_compact_test_block(test)
        )


# =========================================================
# Evidence Cards
# =========================================================

def _evidence_card(
    title: str,
    rows: list[tuple[str, Any]],
) -> KeepTogether:
    content = [
        [
            Paragraph(
                escape(title),
                STYLE_EVIDENCE_TITLE,
            ),
            "",
        ]
    ]

    for key, value in rows:
        content.append(
            [
                Paragraph(escape(key), STYLE_LABEL),
                Paragraph(
                    escape(_text(value)),
                    STYLE_MONO,
                ),
            ]
        )

    table = Table(
        content,
        colWidths=[52 * mm, 111 * mm],
        hAlign="LEFT",
    )

    table.setStyle(
        TableStyle(
            [
                ("SPAN", (0, 0), (-1, 0)),
                ("BACKGROUND", (0, 0), (-1, 0), COLOR_BLUE_LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.6, COLOR_GRAY_200),
                ("LINEBELOW", (0, 1), (-1, -1), 0.25, COLOR_GRAY_200),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 1.65 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.65 * mm),
            ]
        )
    )

    return KeepTogether([table])


def _build_recovery_evidence(
    story: list[Flowable],
    suite_result: dict[str, Any],
) -> None:
    stopped = (
        str(
            suite_result.get(
                "result",
                "",
            )
        ).upper()
        == "STOPPED"
    )

    section_title = (
        "Failure, Recovery, and Stop Evidence"
        if stopped
        else "Failure and Recovery Evidence"
    )

    story.append(
        CondPageBreak(
            100 * mm
        )
    )

    story.extend(
        _section_header(
            "03",
            section_title,
        )
    )

    if stopped:
        aborted_tests = [
            test.get("test_id", "UNKNOWN")
            for test in suite_result.get("tests", [])
            if test.get("result") == "ABORTED"
        ]

        story.append(
            _evidence_card(
                "STOP v1 - Suite Execution Control",
                [
                    (
                        "Suite Result",
                        suite_result.get("result"),
                    ),
                    (
                        "Stop Reason",
                        suite_result.get("stop_reason"),
                    ),
                    (
                        "Executed",
                        (
                            f"{suite_result.get('executed', 0)} / "
                            f"{suite_result.get('total_tests', 0)}"
                        ),
                    ),
                    (
                        "Aborted Tests",
                        (
                            ", ".join(aborted_tests)
                            if aborted_tests
                            else "None"
                        ),
                    ),
                    (
                        "Not Run",
                        suite_result.get("not_run", 0),
                    ),
                    (
                        "Interpretation",
                        (
                            "The active unit was cooperatively cancelled; "
                            "remaining scheduled units were not started."
                        ),
                    ),
                ],
            )
        )

        story.append(
            Spacer(
                1,
                4 * mm,
            )
        )

    # -------------------------------------------------
    # T05 - timeout recovery or cancellation recovery
    # -------------------------------------------------
    t05 = _find_test(
        suite_result,
        "T05",
    )

    if (
        t05
        and t05.get("result") != "NOT_RUN"
    ):
        d = t05.get(
            "details",
            {},
        )

        commands = _safe_get(
            d,
            "details",
            "commands",
            default={},
        ) or {}

        initial = commands.get(
            "initial_read",
            {},
        )

        if (
            t05.get("result") == "ABORTED"
            and initial
        ):
            abort_info = _safe_get(
                d,
                "details",
                "abort",
                default={},
            ) or {}

            abort_recovery = initial.get(
                "abort_recovery",
            ) or {}

            queue_after = (
                abort_recovery.get(
                    "queue_after_reset",
                )
                or initial.get(
                    "queue_state",
                    {},
                )
            )

            story.append(
                _evidence_card(
                    "T05 - READ Abort + Cancellation Recovery",
                    [
                        (
                            "Abort Stage",
                            abort_info.get("stage"),
                        ),
                        (
                            "Stop Reason",
                            abort_info.get("reason"),
                        ),
                        (
                            "Command",
                            (
                                f"CID {_safe_get(initial, 'command', 'cid')} / "
                                f"READ / LBA {_safe_get(initial, 'command', 'lba')}"
                            ),
                        ),
                        (
                            "Host Result",
                            _safe_get(
                                initial,
                                "host",
                                "status",
                            ),
                        ),
                        (
                            "Timed Out",
                            initial.get(
                                "timed_out",
                            ),
                        ),
                        (
                            "Process Termination",
                            abort_recovery.get(
                                "termination",
                            ),
                        ),
                        (
                            "Outstanding After Abort",
                            queue_after.get(
                                "outstanding_cids",
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
                                "next_cid",
                            ),
                        ),
                    ],
                )
            )

            story.append(
                Spacer(
                    1,
                    4 * mm,
                )
            )

        elif initial:
            reset = commands.get(
                "controller_reset",
                {},
            )

            retry = commands.get(
                "retry_read",
                {},
            )

            story.append(
                _evidence_card(
                    "T05 - READ Timeout + Recovery",
                    [
                        (
                            "Initial Command",
                            (
                                f"CID {_safe_get(initial, 'command', 'cid')} / "
                                f"READ / LBA {_safe_get(initial, 'command', 'lba')}"
                            ),
                        ),
                        (
                            "Host Result",
                            _safe_get(
                                initial,
                                "host",
                                "status",
                            ),
                        ),
                        (
                            "Completion",
                            _safe_get(
                                initial,
                                "completion",
                            ),
                        ),
                        (
                            "Outstanding After Timeout",
                            _safe_get(
                                initial,
                                "queue_state",
                                "outstanding_cids",
                            ),
                        ),
                        (
                            "Reset Queue",
                            (
                                f"SQ "
                                f"{_safe_get(reset, 'before', 'sq_head')}/"
                                f"{_safe_get(reset, 'before', 'sq_tail')}"
                                f" -> "
                                f"{_safe_get(reset, 'after', 'sq_head')}/"
                                f"{_safe_get(reset, 'after', 'sq_tail')}, "
                                f"CQ "
                                f"{_safe_get(reset, 'before', 'cq_head')}/"
                                f"{_safe_get(reset, 'before', 'cq_tail')}"
                                f" -> "
                                f"{_safe_get(reset, 'after', 'cq_head')}/"
                                f"{_safe_get(reset, 'after', 'cq_tail')}"
                            ),
                        ),
                        (
                            "CID After Reset",
                            _safe_get(
                                reset,
                                "after",
                                "next_cid",
                            ),
                        ),
                        (
                            "Retry",
                            (
                                f"CID {_safe_get(retry, 'command', 'cid')} / "
                                f"{_safe_get(retry, 'completion', 'status')} / "
                                f"{_safe_get(retry, 'completion', 'data', 'pattern')}"
                            ),
                        ),
                    ],
                )
            )

            story.append(
                Spacer(
                    1,
                    4 * mm,
                )
            )

    # -------------------------------------------------
    # T06 - only show evidence if its commands ran
    # -------------------------------------------------
    t06 = _find_test(
        suite_result,
        "T06",
    )

    if (
        t06
        and t06.get("result") != "NOT_RUN"
    ):
        d = t06.get(
            "details",
            {},
        )

        commands = _safe_get(
            d,
            "details",
            "commands",
            default={},
        ) or {}

        fault_read = commands.get(
            "fault_read",
            {},
        )

        verify_read = commands.get(
            "verify_read",
            {},
        )

        if fault_read:
            story.append(
                _evidence_card(
                    "T06 - Data Miscompare Detection",
                    [
                        (
                            "Fault Command",
                            (
                                f"CID {_safe_get(fault_read, 'command', 'cid')} / "
                                f"READ / LBA {_safe_get(fault_read, 'command', 'lba')}"
                            ),
                        ),
                        (
                            "CQ Status",
                            _safe_get(
                                fault_read,
                                "completion",
                                "status",
                            ),
                        ),
                        (
                            "Returned Data",
                            _safe_get(
                                fault_read,
                                "completion",
                                "data",
                                "pattern",
                            ),
                        ),
                        (
                            "Stored Data Verification",
                            _safe_get(
                                verify_read,
                                "completion",
                                "data",
                                "pattern",
                            ),
                        ),
                        (
                            "Interpretation",
                            (
                                "I/O completed successfully; validator detected "
                                "returned-data mismatch while stored data remained intact."
                            ),
                        ),
                    ],
                )
            )

    # -------------------------------------------------
    # T08 / T09 - skip NOT_RUN and missing evidence.
    # Only request a conditional page break when at least
    # one late evidence block can actually be rendered.
    # -------------------------------------------------
    t08 = _find_test(
        suite_result,
        "T08",
    )

    t09_preview = _find_test(
        suite_result,
        "T09",
    )

    has_late_evidence = any(
        test
        and test.get("result") != "NOT_RUN"
        for test in (
            t08,
            t09_preview,
        )
    )

    if has_late_evidence:
        story.append(
            CondPageBreak(
                67 * mm
            )
        )

    if (
        t08
        and t08.get("result") != "NOT_RUN"
    ):
        d = t08.get(
            "details",
            {},
        )

        read_cmd = _safe_get(
            d,
            "details",
            "commands",
            "read",
            default={},
        ) or {}

        log_entries = _safe_get(
            d,
            "details",
            "log_entries",
            default=[],
        ) or []

        if read_cmd:
            log_entry = (
                log_entries[0]
                if log_entries
                else {}
            )

            story.append(
                _evidence_card(
                    "T08 - NAND Read Failure Correlation",
                    [
                        (
                            "Host Command",
                            (
                                f"CID {_safe_get(read_cmd, 'command', 'cid')} / "
                                f"READ / LBA {_safe_get(read_cmd, 'command', 'lba')}"
                            ),
                        ),
                        (
                            "CQ Completion",
                            (
                                f"{_safe_get(read_cmd, 'completion', 'status')} / "
                                f"{_safe_get(read_cmd, 'completion', 'error')}"
                            ),
                        ),
                        (
                            "Firmware Log CID",
                            log_entry.get("CID"),
                        ),
                        (
                            "Firmware Log LBA",
                            log_entry.get("LBA"),
                        ),
                        (
                            "Firmware Log Error",
                            log_entry.get("Error"),
                        ),
                        (
                            "Correlation",
                            (
                                "CID + Opcode + LBA + Status + Error matched"
                            ),
                        ),
                    ],
                )
            )

            story.append(
                Spacer(
                    1,
                    4 * mm,
                )
            )

    t09 = _find_test(
        suite_result,
        "T09",
    )

    if (
        t09
        and t09.get("result") != "NOT_RUN"
    ):
        d = t09.get(
            "details",
            {},
        )

        commands = _safe_get(
            d,
            "details",
            "commands",
            default={},
        ) or {}

        failed_write = commands.get(
            "failed_write",
            {},
        )

        verify_old = commands.get(
            "verify_old_read",
            {},
        )

        reset = commands.get(
            "controller_reset",
            {},
        )

        retry_write = commands.get(
            "retry_write",
            {},
        )

        readback = commands.get(
            "readback",
            {},
        )

        if failed_write:
            story.append(
                _evidence_card(
                    "T09 - Program Failure + Recovery",
                    [
                        (
                            "Failed WRITE",
                            (
                                f"CID {_safe_get(failed_write, 'command', 'cid')} / "
                                f"{_safe_get(failed_write, 'completion', 'status')} / "
                                f"{_safe_get(failed_write, 'completion', 'error')}"
                            ),
                        ),
                        (
                            "Storage After Failure",
                            _safe_get(
                                verify_old,
                                "completion",
                                "data",
                                "pattern",
                            ),
                        ),
                        (
                            "Reset Preserved CID",
                            _safe_get(
                                reset,
                                "after",
                                "next_cid",
                            ),
                        ),
                        (
                            "Retry WRITE",
                            (
                                f"CID {_safe_get(retry_write, 'command', 'cid')} / "
                                f"{_safe_get(retry_write, 'completion', 'status')}"
                            ),
                        ),
                        (
                            "Final READ",
                            (
                                f"CID {_safe_get(readback, 'command', 'cid')} / "
                                f"{_safe_get(readback, 'completion', 'data', 'pattern')}"
                            ),
                        ),
                        (
                            "Final Queue",
                            (
                                f"SQ "
                                f"{_safe_get(readback, 'queue_state', 'sq_head')}/"
                                f"{_safe_get(readback, 'queue_state', 'sq_tail')}, "
                                f"CQ "
                                f"{_safe_get(readback, 'queue_state', 'cq_head')}/"
                                f"{_safe_get(readback, 'queue_state', 'cq_tail')}, "
                                f"next CID "
                                f"{_safe_get(readback, 'queue_state', 'next_cid')}"
                            ),
                        ),
                    ],
                )
            )


# =========================================================
# Technical Notes
# =========================================================

def _build_technical_notes(
    story: list[Flowable],
) -> None:
    story.append(PageBreak())

    story.extend(
        _section_header(
            "04",
            "Technical Notes and Scope",
        )
    )

    notes = [
        (
            "Queue Model",
            (
                "The project models Submission Queue (SQ), Completion Queue (CQ), "
                "CID allocation, queue head/tail progression, and logical doorbell "
                "events on the Host side."
            ),
        ),
        (
            "Mock Controller",
            (
                "The controller executes in a separate Python subprocess and receives "
                "Host-assigned commands and CIDs."
            ),
        ),
        (
            "Fault Injection",
            (
                "Timeout, NAND_READ_FAIL, NAND_PROGRAM_FAIL, and data miscompare "
                "faults are deterministic and designed for validation workflow "
                "demonstration."
            ),
        ),
        (
            "Firmware Log",
            (
                "Runtime firmware-style log entries are generated by the Mock "
                "Controller process and can be correlated with command results by "
                "CID, LBA, status, and error."
            ),
        ),
        (
            "STOP v1",
            (
                "Cancellation is cooperative. Active fake_nvme subprocesses can be "
                "terminated and recovered through simulated controller reset; "
                "arbitrary Python deadlocks or non-cooperative infinite loops are "
                "outside the v1 stop guarantee."
            ),
        ),
        (
            "Hardware Scope",
            (
                "This project is a Host-side logical NVMe validation simulation. "
                "It does not emulate or claim real PCIe MMIO, DMA, PRP/SGL, "
                "MSI/MSI-X, FTL, NAND media behavior, or physical SSD firmware "
                "validation."
            ),
        ),
    ]

    story.append(_key_value_table(notes))
    story.append(Spacer(1, 7 * mm))

    story.append(
        Paragraph(
            (
                "<b>Purpose:</b> demonstrate validation design, automation structure, "
                "failure handling, recovery logic, queue-state reasoning, and evidence "
                "correlation in a deterministic mock environment."
            ),
            STYLE_NOTE,
        )
    )


# =========================================================
# Public API
# =========================================================

def generate_suite_report(
    suite_result: dict[str, Any],
    output_dir: Path | None = None,
) -> Path:
    generated_at = datetime.now()

    suite_id = suite_result.get("suite_id", "UNKNOWN")

    if output_dir is None:
        output_dir = PROJECT_ROOT / "reports" / suite_id

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    filename = _make_filename(
        suite_id=suite_id,
        generated_at=generated_at,
    )

    output_path = output_dir / filename

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=17 * mm,
        leftMargin=17 * mm,
        topMargin=20 * mm,
        bottomMargin=18 * mm,
        title=f"{suite_id} Validation Report",
        author="Automation Mock NVMe Validation",
        subject="Automated NVMe validation report",
    )

    story: list[Flowable] = []

    _build_cover(
        story=story,
        suite_result=suite_result,
        generated_at=generated_at,
    )

    _build_test_summary(
        story=story,
        suite_result=suite_result,
    )

    _build_detailed_results(
        story=story,
        suite_result=suite_result,
    )

    _build_recovery_evidence(
        story=story,
        suite_result=suite_result,
    )

    _build_technical_notes(
        story=story,
    )

    doc.build(
        story,
        onFirstPage=_draw_header_footer,
        onLaterPages=_draw_header_footer,
    )

    return output_path
