from services.groq_service import fetch_content


def generate_report_text(topic: str, num_pages: int = 3) -> str:
    return fetch_content(topic, num_pages)
