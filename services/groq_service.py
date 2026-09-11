import os
import re
import time
import logging
from groq import Groq

_logger = logging.getLogger(__name__)
_client = None

# Primary model with fallback chain to prevent rate limit (429) failures
MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "groq/compound-mini"]
MODEL = MODELS[0]

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


def _chat(messages, max_tokens=850, temperature=0.7):
    client = get_groq_client()
    last_error = None

    for current_model in MODELS:
        for attempt in range(2):
            try:
                response = client.chat.completions.create(
                    model=current_model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                content = (response.choices[0].message.content or "").strip()
                if content:
                    return content
                # If model returned empty (e.g. reasoning model exhausted tokens), retry
                _logger.warning("Model %s returned empty response, retrying...", current_model)
            except Exception as exc:
                last_error = exc
                err_str = str(exc)
                if "429" in err_str or "rate_limit" in err_str.lower():
                    # Parse retry delay if provided
                    match = re.search(r"try again in ([\d\.]+)s", err_str)
                    wait_time = float(match.group(1)) if match else (2.0 * (attempt + 1))
                    wait_time = min(wait_time, 4.0)
                    _logger.info("Rate limit hit on %s. Waiting %.1fs...", current_model, wait_time)
                    time.sleep(wait_time)
                else:
                    _logger.warning("Error with model %s (attempt %d): %s", current_model, attempt + 1, exc)
                    time.sleep(0.5)

    raise GroqRequestError(f"Error fetching content from Groq after fallback attempts: {last_error}")


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
        max_tokens=500,
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
        titles = [f"Section {i+1}" for i in range(num_sections)]

    return titles[:num_sections]


def _generate_intro(topic: str, target_words: int) -> str:
    tokens = min(850, int(target_words * 1.6) + 150)
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
        max_tokens=tokens,
    )


def _generate_section(topic: str, section_title: str, target_words: int) -> str:
    tokens = min(950, int(target_words * 1.6) + 150)
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
        max_tokens=tokens,
    )


def _generate_conclusion(topic: str, target_words: int) -> str:
    tokens = min(750, int(target_words * 1.6) + 150)
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
        max_tokens=tokens,
    )


def fetch_content(topic: str, num_pages: int) -> str:
    """
    Generates a report in chunks (outline -> intro -> sections -> conclusion)
    and stitches them together, so long reports don't hit token limits or
    trigger the model to refuse/summarize instead of writing in full.
    """
    target_words = num_pages * WORDS_PER_PAGE

    # Reserve ~15% for intro, ~15% for conclusion, rest split across sections
    intro_words = max(150, int(target_words * 0.15))
    conclusion_words = max(150, int(target_words * 0.15))
    body_words = max(300, target_words - intro_words - conclusion_words)

    # Cap at 7 sections to avoid excessive sequential calls while still delivering rich length
    num_sections = max(2, min(7, round(body_words / WORDS_PER_SECTION_TARGET)))
    words_per_section = body_words // num_sections

    section_titles = _generate_outline(topic, num_sections)
    time.sleep(0.3)

    parts = [_generate_intro(topic, intro_words)]

    for title in section_titles:
        time.sleep(0.3)
        parts.append(_generate_section(topic, title, words_per_section))

    time.sleep(0.3)
    parts.append(_generate_conclusion(topic, conclusion_words))

    return "\n\n".join(parts)
