import re


def slugify(text: str, max_length: int = 40) -> str:
    """Turn a topic string into a filesystem-safe filename fragment."""
    text = re.sub(r"[^a-zA-Z0-9\s_-]", "", text).strip()
    text = re.sub(r"\s+", "_", text)
    return text[:max_length] or "report"
