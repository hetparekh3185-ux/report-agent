import re
import unicodedata

BOLD_PATTERN = re.compile(r"\*\*(.+?)\*\*")

# "Smart" Unicode punctuation that base-14 PDF fonts and the default
# docx font either render as a missing-glyph box or map inconsistently.
# Normalize to plain ASCII before anything gets laid out.
_UNICODE_REPLACEMENTS = {
    "\u2013": "-",    # en dash
    "\u2014": "--",   # em dash
    "\u2018": "'",    # left single quote
    "\u2019": "'",    # right single quote
    "\u201c": '"',    # left double quote
    "\u201d": '"',    # right double quote
    "\u2026": "...",  # ellipsis
    "\u2022": "-",    # bullet
    "\u00a0": " ",    # non-breaking space
}


def sanitize_text(text: str) -> str:
    for src, dst in _UNICODE_REPLACEMENTS.items():
        text = text.replace(src, dst)
    # Catch anything else non-ASCII that slipped through (rare symbols,
    # accented characters the model sometimes adds) by decomposing and
    # dropping anything that still isn't plain ASCII.
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    return text


_TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
_TABLE_SEP_RE = re.compile(r"^\s*\|?[\s:\-]+\|[\s:\-\|]*$")


def _split_table_row(line: str) -> list:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [cell.strip() for cell in line.split("|")]


def parse_blocks(content: str):
    """
    Parses markdown-ish report text into a list of blocks:
      {"type": "heading", "level": 1|2|3, "text": str}
      {"type": "table", "rows": [[cell, ...], ...]}   # rows[0] is header
      {"type": "para", "text": str}

    Text has already been run through sanitize_text(), so downstream
    renderers never have to deal with characters their fonts can't
    display.
    """
    content = sanitize_text(content)
    lines = content.split("\n")
    blocks = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i].strip()

        if not line:
            i += 1
            continue

        # markdown table: header row + separator row ("|---|---|") + data rows
        if (
            _TABLE_ROW_RE.match(line)
            and i + 1 < n
            and _TABLE_SEP_RE.match(lines[i + 1].strip())
        ):
            rows = [_split_table_row(line)]
            i += 2  # skip header + separator row
            while i < n and _TABLE_ROW_RE.match(lines[i].strip()):
                rows.append(_split_table_row(lines[i].strip()))
                i += 1
            blocks.append({"type": "table", "rows": rows})
            continue

        if line.startswith("### "):
            blocks.append({"type": "heading", "level": 3, "text": line[4:]})
        elif line.startswith("## "):
            blocks.append({"type": "heading", "level": 2, "text": line[3:]})
        elif line.startswith("# "):
            blocks.append({"type": "heading", "level": 1, "text": line[2:]})
        else:
            blocks.append({"type": "para", "text": line})

        i += 1

    return blocks
