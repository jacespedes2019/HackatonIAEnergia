import re
from datetime import datetime
import uuid

# All comments in English.

def normalize_text(text: str) -> str:
    """Normalize user text: lowercase, remove extra spaces and punctuation noise."""
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^a-záéíóúñ0-9\s]", "", text)
    return text


def format_currency_millions(cop: int) -> str:
    """Format COP integer into human-readable millions string."""
    try:
        millions = cop / 1_000_000
        return f"{millions:.1f} millones"
    except Exception:
        return str(cop)


def generate_filename(prefix: str = "file", extension: str = "mp3") -> str:
    """Generate a unique filename with UUID."""
    uid = uuid.uuid4().hex
    return f"{prefix}_{uid}.{extension}"


def timestamp_now() -> str:
    """Return current UTC timestamp in ISO format."""
    return datetime.utcnow().isoformat()


def safe_str(text: str) -> str:
    """Ensure text is a safe non-None string before sending to TTS."""
    if text is None:
        return ""
    return str(text).strip()