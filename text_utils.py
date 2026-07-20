"""Small text normalization utilities without NLP model dependencies."""
import re


def clean_text(text: str) -> str:
    """Normalize text before embedding and keyword processing."""
    if not text or not isinstance(text, str):
        return ""

    text = str(text)
    text = re.sub(r"http\S+\s*", " ", text)
    text = re.sub(r"\bRT\b|\bcc\b", " ", text)
    text = re.sub(r"#\S+", "", text)
    text = re.sub(r"@\S+", " ", text)
    text = re.sub(r"[^\w\s\.\+\#/]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.lower().strip()
