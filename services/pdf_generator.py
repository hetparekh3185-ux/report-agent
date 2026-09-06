from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER

from utils.content_blocks import parse_blocks, BOLD_PATTERN


def _convert_markdown_bold(text: str) -> str:
    """
    ReportLab's Paragraph understands a small set of HTML-like tags
    natively (including <b>), but NOT markdown **bold** syntax — passed
    through as-is, the raw asterisks show up literally in the PDF.
    """
    return BOLD_PATTERN.sub(r"<b>\1</b>", text)


def _build_table_flowable(rows: list, cell_style) -> Table:
    ncols = max(len(r) for r in rows)
    data = []
    for row_cells in rows:
        row = []
        for c in range(ncols):
            text = row_cells[c] if c < len(row_cells) else ""
            row.append(Paragraph(_convert_markdown_bold(text), cell_style))
        data.append(row)

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9D9D9")),
        ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


def build_pdf(topic: str, body_text: str, output_path: str) -> str:
    styles = getSampleStyleSheet()

    styles["Title"].alignment = TA_CENTER
    styles["Title"].fontName = "Times-Bold"

    for level_name in ("Heading1", "Heading2", "Heading3"):
        styles[level_name].fontName = "Times-Bold"

    body_style = styles["BodyText"]
    body_style.alignment = TA_JUSTIFY
    body_style.fontName = "Times-Roman"
    body_style.fontSize = 11

    cell_style = getSampleStyleSheet()["BodyText"]
    cell_style.fontName = "Times-Roman"
    cell_style.fontSize = 9
    cell_style.leading = 11

    doc = SimpleDocTemplate(output_path, pagesize=LETTER, topMargin=inch, bottomMargin=inch)
    story = [Paragraph(_convert_markdown_bold(topic), styles["Title"]), Spacer(1, 16)]

    for block in parse_blocks(body_text):
        if block["type"] == "table":
            story.append(_build_table_flowable(block["rows"], cell_style))
            story.append(Spacer(1, 10))
            continue

        if block["type"] == "heading":
            style_name = {1: "Heading1", 2: "Heading2", 3: "Heading3"}[block["level"]]
            story.append(Paragraph(_convert_markdown_bold(block["text"]), styles[style_name]))
        else:
            story.append(Paragraph(_convert_markdown_bold(block["text"]), body_style))
        story.append(Spacer(1, 6))

    doc.build(story)
    return output_path
