import google.generativeai as genai
from app.models import Lead

# All comments in English.

def transcribe_audio(file_path: str, mime_type: str = "audio/webm") -> str:
    """
    Transcribe audio using Gemini 2.5 Flash (supports audio in generateContent).
    """
    model = genai.GenerativeModel("models/gemini-2.5-flash")

    with open(file_path, "rb") as f:
        audio_bytes = f.read()

    audio_part = {
        "mime_type": mime_type,
        "data": audio_bytes,
    }

    prompt = "Transcribe exactamente lo que dice la persona en español. Solo la transcripción."

    response = model.generate_content([audio_part, prompt])

    return (response.text or "").strip()


import google.generativeai as genai
from app.models import Lead

# STT function stays as you already have it:
def transcribe_audio(file_path: str, mime_type: str = "audio/webm") -> str:
    """Transcribe audio using Gemini 2.5 Flash (supports audio in generateContent)."""
    model = genai.GenerativeModel("models/gemini-2.5-flash")

    with open(file_path, "rb") as f:
        audio_bytes = f.read()

    audio_part = {
        "mime_type": mime_type,
        "data": audio_bytes,
    }

    prompt = (
        "Transcribe exactamente lo que dice la persona en español. "
        "Responde solo con la transcripción, sin explicaciones."
    )

    response = model.generate_content([audio_part, prompt])
    return (response.text or "").strip()


def build_response(lead: Lead, user_text: str, intent: str) -> str:
    """
    Use Gemini to generate a Spanish response for a car sales call.
    The response should be short (max 3 sentences) and polite.
    We DO NOT use 'system' role, only a single prompt string.
    """
    model = genai.GenerativeModel("models/gemini-2.5-pro")

    system_block = (
        "Eres un asistente profesional de ventas telefónicas para Domu Autos en Colombia. "
        "Siempre respondes en español latino, con máximo 3 oraciones, tono respetuoso y claro.\n\n"
        "Información del cliente potencial y del vehículo:\n"
        f"- Nombre del cliente: {lead.name}\n"
        f"- Modelo del carro: {lead.car_model}\n"
        f"- Nombre comercial del carro: {lead.car_name}\n"
        f"- Precio del carro en COP: {lead.car_price_cop}\n\n"
        "Intenciones:\n"
        "- NOT_INTERESTED: agradecer su tiempo, respetar totalmente la decisión y confirmar que no se insistirá.\n"
        "- FOLLOW_UP: agradecer y decir que se le contactará en otro momento, sin presionar.\n"
        "- INTERESTED: agradecer y decir que un asesor lo contactará con más detalles y opciones de financiación.\n"
        "- NEUTRAL: dar un cierre amable y ofrecer otros canales si desea más información.\n"
    )

    user_block = (
        f"Texto exacto que dijo el usuario: \"{user_text}\"\n"
        f"Intención detectada: {intent}\n\n"
        "Genera la respuesta final que se dirá al usuario ahora."
    )

    # Single prompt string, no roles
    full_prompt = system_block + "\n\n" + user_block

    response = model.generate_content(full_prompt)
    return (response.text or "").strip()