from __future__ import annotations

from html import escape
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def build_search_report_pdf(search: Any) -> bytes:
    buffer = BytesIO()
    navy = colors.HexColor("#13243A")
    teal = colors.HexColor("#0D7C72")
    coral = colors.HexColor("#E56748")
    pale = colors.HexColor("#F1F6F7")
    line = colors.HexColor("#D5E0E4")
    muted = colors.HexColor("#5D6C79")

    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=19,
        leading=23,
        textColor=colors.black,
        alignment=TA_CENTER,
        spaceAfter=4 * mm,
    )
    subtitle = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontSize=9,
        leading=13,
        textColor=muted,
        alignment=TA_CENTER,
        spaceAfter=6 * mm,
    )
    heading = ParagraphStyle(
        "ResultHeading",
        parent=styles["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=14,
        textColor=navy,
        spaceAfter=1.5 * mm,
    )
    body = ParagraphStyle(
        "ReportBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=navy,
        spaceAfter=1.5 * mm,
    )
    small = ParagraphStyle(
        "ReportSmall",
        parent=body,
        fontSize=7.5,
        leading=10,
        textColor=muted,
    )

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=17 * mm,
        rightMargin=17 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title=f"Recommendation Report {search.id}",
        author="Indian Standards Finder",
    )

    story = [
        Paragraph("Indian Standards Recommendation Report", title),
        Paragraph("Explainable retrieval results for procurement review", subtitle),
    ]
    metadata = Table(
        [
            ["Search ID", str(search.id), "Created", escape(search.created_at)],
            ["Source", escape(search.source_name or search.source_type), "Mode", escape(search.mode)],
            ["Results", str(search.result_count), "Status", "For technical review"],
        ],
        colWidths=[26 * mm, 62 * mm, 24 * mm, 64 * mm],
    )
    metadata.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), pale),
                ("BACKGROUND", (2, 0), (2, -1), pale),
                ("GRID", (0, 0), (-1, -1), 0.5, line),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.8),
                ("TEXTCOLOR", (0, 0), (-1, -1), navy),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend(
        [
            metadata,
            Spacer(1, 4 * mm),
            Paragraph("Procurement requirement", heading),
            Paragraph(escape(search.query), body),
            Spacer(1, 2 * mm),
        ]
    )

    for rank, result in enumerate(search.results, start=1):
        confidence = round(float(result.get("confidence_score", 0)) * 100)
        header = Table(
            [
                [
                    Paragraph(
                        f"{rank}. {escape(str(result.get('standard_code', '')))}",
                        heading,
                    ),
                    Paragraph(
                        f"Score {escape(str(result.get('score', '')))} | Confidence {confidence}%",
                        small,
                    ),
                ]
            ],
            colWidths=[112 * mm, 64 * mm],
        )
        header.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), pale),
                    ("BOX", (0, 0), (-1, -1), 0.7, teal),
                    ("LINEBEFORE", (0, 0), (0, 0), 3, teal),
                    ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        terms = ", ".join(result.get("matched_terms", [])) or "No direct terms recorded"
        evidence = result.get("evidence_clauses", [])
        applicability = escape(str(result.get("mandatory_hint", "Not recorded")))
        source_url = escape(str(result.get("source_url", "")), quote=True)
        block = [
            header,
            Spacer(1, 1.5 * mm),
            Paragraph(f"<b>{escape(str(result.get('title', '')))}</b>", body),
            Paragraph(escape(str(result.get("reason", ""))), body),
            Paragraph(
                f"<b>Category:</b> {escape(str(result.get('category', '')))} / {escape(str(result.get('subcategory', '')))}<br/>"
                f"<b>Verification:</b> {escape(str(result.get('verify_status', '')).replace('_', ' '))}<br/>"
                f"<b>Applicability:</b> {applicability}<br/>"
                f"<b>Matched terms:</b> {escape(terms)}<br/>"
                f"<b>Source:</b> <link href=\"{source_url}\" color=\"#0D7C72\">{source_url}</link>",
                small,
            ),
        ]
        if evidence:
            block.append(
                Paragraph(
                    "<b>Supporting clause:</b> " + escape(str(evidence[0])),
                    small,
                )
            )
        block.extend([Spacer(1, 2.5 * mm)])
        story.append(KeepTogether(block))

    disclaimer = Table(
        [[Paragraph(
            "This report identifies potentially applicable standards for technical review. It is not a legal determination of applicability or mandatory certification status.",
            small,
        )]],
        colWidths=[176 * mm],
    )
    disclaimer.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.7, coral),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(disclaimer)

    document.build(story)
    return buffer.getvalue()
