import os
from groq import Groq

_client = None


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
            # Most common cause: an httpx version newer than what this
            # groq SDK version expects (httpx 0.28+ dropped the `proxies`
            # kwarg that older groq releases still pass internally).
            raise GroqConfigError(
                f"Failed to create the Groq client — likely a groq/httpx version "
                f"mismatch in requirements.txt. Original error: {exc}"
            ) from exc
    return _client


def fetch_content(topic: str, num_pages: int) -> str:
    """Same prompt/params as your CLI script, minus the sys.exit on failure."""
    words_per_page = 350
    target_words = num_pages * words_per_page

    prompt = f"""
    Write a comprehensive report on the topic: "{topic}"

    Requirements:
    - Target length: approximately {target_words} words ({num_pages} pages)
    - Structure with clear headings and subheadings (use markdown: #, ##, ###)
    - Include an introduction, main body with multiple sections, and conclusion
    - Use professional, informative tone
    - Include relevant details, examples, and analysis
    - Format with clear section breaks
    """

    client = get_groq_client()
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional report writer. Create well-structured, informative reports.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=4000,
        )
        return response.choices[0].message.content
    except Exception as exc:
        raise GroqRequestError(f"Error fetching content from Groq: {exc}") from exc