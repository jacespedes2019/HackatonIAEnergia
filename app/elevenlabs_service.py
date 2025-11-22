import os
import requests

from app.config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, AUDIO_DIR, BASE_PUBLIC_URL
from app.utils import generate_filename, safe_str

# All comments in English.

def generate_tts(text: str, prefix: str = "tts") -> str:
    """
    Generate an MP3 file using ElevenLabs TTS and return a public URL
    that can be used by the frontend (e.g. <audio src="...">).
    """
    text = safe_str(text)
    filename = generate_filename(prefix=prefix, extension="mp3")
    file_path = os.path.join(AUDIO_DIR, filename)

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"

    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
    }

    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
    }

    res = requests.post(url, json=payload, headers=headers)
    res.raise_for_status()

    with open(file_path, "wb") as f:
        f.write(res.content)

    return f"{BASE_PUBLIC_URL}/audio/{filename}"