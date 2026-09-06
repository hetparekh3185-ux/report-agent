import os
import re
from groq import Groq

_client = None

MODEL = "openai/gpt-oss-120b"
WORDS_PER_PAGE = 350
WORDS_PER_SECTION_TARGET = 700  # roughly 2 pages of content per section call


class GroqConfigError(RuntimeError):
    """Raised when the API key is missing — caught in app.py, doesn't kill the server."""


class GroqRequestError(RuntimeError):
    """Raised when the Groq API call itself fails."""


def get_groq_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise GroqConfigError(
                "GROQ_API_KEY not found in environment variables. Add it to your .env file."
            )
        try:
            _client = Groq(api_key=api_key)
        except TypeError as exc:
            raise GroqConfigError(
                f"Failed to create the Groq client — likely a groq/httpx version "
                f"mismatch in requirements.txt. Original error: {exc}"
            ) from exc
    return _client


def _chat(messages, max_tokens=1500, temperature=0.7):
    client = get_groq_client()
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        raise GroqRequestError(f"Error fetching content from Groq: {exc}") from exc


def _generate_outline(topic: str, num_sections: int) -> list[str]:
    """Ask the model for just a numbered list of section headings."""
    prompt = f"""
    Create an outline for a comprehensive report on the topic: "{topic}"

    Give exactly {num_sections} main section headings (not counting the
    introduction or conclusion — those are handled separately).
    Return ONLY a numbered list of short section titles, one per line,
    e.g.:
    1. Background and Context
    2. Key Mechanisms
    ...
    No extra commentary, no markdown symbols other than the numbers.
    """
    raw = _chat(
        [
            {"role": "system", "content": "You are an expert report planner. Follow the requested format exactly."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=400,
        temperature=0.5,
    )

    titles = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        # strip leading "1.", "1)", "-", etc.
        cleaned = re.sub(r"^\s*[\d]+[\.\)]\s*", "", line)
        cleaned = re.sub(r"^[-*]\s*", "", cleaned)
        if cleaned:
            titles.append(cleaned)

    if not titles:
        # fallback if parsing fails — generic sections
        titles = [f"Section {i+1}" for i in range(num_sections)]

    return titles[:num_sections]


def _generate_intro(topic: str, target_words: int) -> str:
    prompt = f"""
    Write ONLY the introduction section for a professional report on: "{topic}"
    Target length: approximately {target_words} words.
    Start with a "# {topic}" markdown H1 heading, then an "## Introduction" H2 heading,
    then the introduction text. Professional, informative tone. No conclusion, no other sections.
    """
    return _chat(
        [
            {"role": "system", "content": "You are a professional report writer."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=1200,
    )


def _generate_section(topic: str, section_title: str, target_words: int) -> str:
    prompt = f"""
    Write ONLY the section titled "{section_title}" for a professional report on: "{topic}"

    Requirements:
    - Start with "## {section_title}" as a markdown H2 heading
    - Target length: approximately {target_words} words
    - Use "### " subheadings where useful
    - Professional, informative tone with relevant details, examples, and analysis
    - Do NOT write an introduction or conclusion for the overall report — only this section
    - Do NOT comment on length or add meta remarks — write the content directly
    """
    return _chat(
        [
            {"role": "system", "content": "You are a professional report writer."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=1800,
    )


def _generate_conclusion(topic: str, target_words: int) -> str:
    prompt = f"""
    Write ONLY the conclusion section for a professional report on: "{topic}"
    Target length: approximately {target_words} words.
    Start with "## Conclusion" as a markdown H2 heading, then the conclusion text.
    Summarize key points and close professionally. No other sections.
    """
    return _chat(
        [
            {"role": "system", "content": "You are a professional report writer."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=800,
    )


def fetch_content(topic: str, num_pages: int) -> str:
    """
    Generates a report in chunks (outline -> intro -> sections -> conclusion)
    and stitches them together, so long reports don't hit token limits or
    trigger the model to refuse/summarize instead of writing in full.

    Same signature as before — safe drop-in replacement.
    """
    target_words = num_pages * WORDS_PER_PAGE

    # Reserve ~15% for intro, ~15% for conclusion, rest split across sections
    intro_words = max(150, int(target_words * 0.15))
    conclusion_words = max(150, int(target_words * 0.15))
    body_words = max(300, target_words - intro_words - conclusion_words)

    num_sections = max(2, min(10, round(body_words / WORDS_PER_SECTION_TARGET)))
    words_per_section = body_words // num_sections

    section_titles = _generate_outline(topic, num_sections)

    parts = [_generate_intro(topic, intro_words)]
    for title in section_titles:
        parts.append(_generate_section(topic, title, words_per_section))
    parts.append(_generate_conclusion(topic, conclusion_words))

    return "\n\n".join(parts)
