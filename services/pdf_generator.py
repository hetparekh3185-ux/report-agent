import re
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER

BOLD_PATTERN = re.compile(r"\*\*(.+?)\*\*")


def _convert_markdown_bold(text: str) -> str:
    """
    ReportLab's Paragraph understands a small set of HTML-like tags
    natively (including <b>), but NOT markdown **bold** syntax — passed
    through as-is, the raw asterisks show up literally in the PDF.
    """
    return BOLD_PATTERN.sub(r"<b>\1</b>", text)


def build_pdf(topic: str, body_text: str, output_path: str) -> str:
    styles = getSampleStyleSheet()

    styles["Title"].alignment = TA_CENTER
    styles["Title"].fontName = "Times-Bold"

    for level_name in ("Heading1", "Heading2", "Heading3"):
        # These default to Helvetica-Bold in ReportLab's sample stylesheet
        # and were never overridden, so headings rendered in the wrong
        # font family entirely (same class of bug as the docx version,
        # different underlying cause: no theme quirk here, just a missed
        # override).
        styles[level_name].fontName = "Times-Bold"

    body_style = styles["BodyText"]
    body_style.alignment = TA_JUSTIFY
    body_style.fontName = "Times-Roman"
    body_style.fontSize = 11

    doc = SimpleDocTemplate(output_path, pagesize=LETTER, topMargin=inch, bottomMargin=inch)
    story = [Paragraph(_convert_markdown_bold(topic), styles["Title"]), Spacer(1, 16)]

    for raw_line in body_text.split("\n"):
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("# "):
            story.append(Paragraph(_convert_markdown_bold(line[2:]), styles["Heading1"]))
        elif line.startswith("## "):
            story.append(Paragraph(_convert_markdown_bold(line[3:]), styles["Heading2"]))
        elif line.startswith("### "):
            story.append(Paragraph(_convert_markdown_bold(line[4:]), styles["Heading3"]))
        else:
            story.append(Paragraph(_convert_markdown_bold(line), body_style))
        story.append(Spacer(1, 6))

    doc.build(story)
    return output_path
