from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "demo_procurement_specification.pdf"


def build_pdf() -> Path:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    navy = colors.HexColor("#13243A")
    teal = colors.HexColor("#0D7C72")
    pale = colors.HexColor("#EEF5F5")
    line = colors.HexColor("#D6E0E4")
    muted = colors.HexColor("#5E6E7D")

    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "DocumentTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.black,
        alignment=TA_CENTER,
        spaceAfter=5 * mm,
    )
    subtitle = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=muted,
        alignment=TA_CENTER,
        spaceAfter=7 * mm,
    )
    section = ParagraphStyle(
        "Section",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.black,
        spaceBefore=4 * mm,
        spaceAfter=2 * mm,
    )
    body = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=navy,
        spaceAfter=2.5 * mm,
    )
    clause = ParagraphStyle(
        "Clause",
        parent=body,
        leftIndent=5 * mm,
        firstLineIndent=-5 * mm,
        spaceAfter=3.2 * mm,
    )
    small = ParagraphStyle(
        "Small",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=muted,
    )

    document = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=19 * mm,
        rightMargin=19 * mm,
        topMargin=17 * mm,
        bottomMargin=16 * mm,
        title="Demo Procurement Specification",
        author="Indian Standards Finder Demo",
    )

    story = [
        Paragraph("Demo Procurement Specification", title),
        Paragraph(
            "Municipal Infrastructure and Hospital Upgrade Package",
            subtitle,
        ),
    ]

    metadata = Table(
        [
            ["Tender Reference", "DEMO/ISF/2026/01", "Issue Date", "29 September 2026"],
            ["Purchaser", "Demo Municipal Authority", "Evaluation", "Technical compliance"],
        ],
        colWidths=[31 * mm, 58 * mm, 27 * mm, 56 * mm],
    )
    metadata.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), pale),
                ("BACKGROUND", (2, 0), (2, -1), pale),
                ("TEXTCOLOR", (0, 0), (-1, -1), navy),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.2),
                ("GRID", (0, 0), (-1, -1), 0.6, line),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.extend(
        [
            metadata,
            Spacer(1, 5 * mm),
            Paragraph("Scope of Procurement", section),
            Paragraph(
                "The purchaser invites technically compliant supplies for civil, street-lighting, water-quality, and fire-safety works. Bidders shall identify applicable Indian Standards, provide test certificates, and state any deviations in the technical offer.",
                body,
            ),
            Paragraph("Technical Requirements", section),
            Paragraph(
                "<b>1. Reinforcement steel</b> Supply Fe 500D high-strength deformed TMT reinforcement bars for RCC slab, beam, and column construction. Bars shall be suitable for concrete reinforcement and accompanied by manufacturer test certificates.",
                clause,
            ),
            Paragraph(
                "<b>2. LED street lighting</b> Supply outdoor LED street-light luminaires for municipal roads. Each luminaire shall have weatherproof housing, suitable optical performance, and electrical safety provisions for continuous outdoor operation.",
                clause,
            ),
            Paragraph(
                "<b>3. Drinking-water quality testing</b> Conduct potable-water testing for physical, chemical, and microbiological parameters, including pH, turbidity, fluoride, nitrate, total dissolved solids, and coliform organisms.",
                clause,
            ),
            Paragraph(
                "<b>4. Hospital fire protection</b> Provide and commission a fire hydrant and hose-reel system for the hospital building, including landing valves, hoses, branch pipes, pumps, and associated accessories.",
                clause,
            ),
            Paragraph("Compliance Submission", section),
            Paragraph(
                "The bidder shall submit a clause-by-clause compliance statement, applicable Indian Standard references, product data sheets, valid test reports, and details of proposed inspection and acceptance testing.",
                body,
            ),
            Spacer(1, 3 * mm),
        ]
    )

    footer = Table(
        [[Paragraph("Demonstration document for evaluating standards recommendation and clause evidence extraction.", small)]],
        colWidths=[172 * mm],
    )
    footer.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.8, teal),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(footer)

    document.build(story)
    return OUTPUT


if __name__ == "__main__":
    print(build_pdf())
