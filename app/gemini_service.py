import json
import re
from typing import List, Dict

import google.generativeai as genai
from faster_whisper import WhisperModel

from app.models import Lead

# All comments in English.

# ---------- Global models ----------

# Local STT model (tune size: "tiny", "base", "small")
whisper_model = WhisperModel(
    "base",              # better quality for Spanish than tiny/small-int8
    device="cpu",
    compute_type="int8"  # best speed/quality on CPU
)

# Gemini models for text tasks
intent_model = genai.GenerativeModel("models/gemini-flash-latest")
reply_model = genai.GenerativeModel("models/gemini-flash-latest")


# ------------------------------------------------------------
#  TRANSCRIBE + INTENT WITH FASTER WHISPER + GEMINI
# ------------------------------------------------------------
def transcribe_and_analyze(file_path: str, mime_type: str = "audio/webm"):
    """
    Transcribe audio using Faster Whisper + classify intent using Gemini.
    """

    # ---------- 1) LOCAL FASTER WHISPER ----------
    print("🎤 Iniciando transcripción con Faster Whisper...")

    segments, info = whisper_model.transcribe(
        file_path,
        language="es",
        beam_size=5,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 300},
    )

    # Idioma detectado
    print("🌎 Idioma detectado:", info.language)
    print("📊 Probabilidad idioma:", info.language_probability)

    # Imprimir cada segmento
    full_text = []
    print("🔎 Segmentos detectados por Whisper:")
    for seg in segments:
        print(f"  🟦 [{seg.start:.2f}s → {seg.end:.2f}s] {seg.text}")
        full_text.append(seg.text)

    # Texto final limpio
    transcript = " ".join(full_text).strip()
    print("📝 TRANSCRIPCIÓN FINAL:", transcript if transcript else "<vacía>")

    if not transcript:
        print("⚠️ Whisper no detectó texto. Se usa NEUTRAL.")
        return {
            "transcript": "",
            "intent": "NEUTRAL",
        }

    # ---------- 2) INTENT WITH GEMINI ----------
    print("🤖 Clasificando intención con Gemini...")

    prompt = f"""
Clasifica la intención del cliente en UNA sola palabra.
Texto del cliente:
\"\"\"{transcript}\"\"\"\n
Responde SOLO una etiqueta:
NOT_INTERESTED | INTERESTED | FOLLOW_UP | NEUTRAL
"""

    try:
        resp = intent_model.generate_content(prompt)
        intent = (resp.text or "").strip().upper()
        print("🔮 INTENCIÓN DETECTADA:", intent)
    except Exception as e:
        print("❌ Error clasificando intención:", e)
        intent = "NEUTRAL"

    if intent not in {"NOT_INTERESTED", "INTERESTED", "FOLLOW_UP", "NEUTRAL"}:
        print("⚠️ Intent inválido. Se fuerza a NEUTRAL")
        intent = "NEUTRAL"

    return {
        "transcript": transcript,
        "intent": intent,
    }

# ------------------------------------------------------------
#  BUILD RESPONSE (GEMINI TEXT-ONLY, WITH HISTORY)
# ------------------------------------------------------------
def build_response(
    lead: Lead,
    user_text: str,
    intent: str,
    history: List[Dict[str, str]],
) -> str:
    """
    Use Gemini to generate a short, natural Spanish sales-call reply.
    """

    # Only last 2 turns to keep prompt small & very fast
    history_block = ""
    for turn in history[-2:]:
        history_block += f"Usuario: {turn.get('user')}\nAgente: {turn.get('agent')}\n\n"

    # System instructions
    system_block = f"""
Eres un asesor comercial colombiano, profesional y cercano.
Vendes servicios de lavado detallado y fotografía profesional
para que el cliente venda su carro rápido y sin bajar el precio.

Respuestas SIEMPRE cortas (máximo 3 oraciones, 12 palabras c/u).
No suenes robótico. Sé directo, claro y humano.

Cliente: {lead.name}
Vehículo: {lead.car_name} {lead.car_model}
Precio estimado: {lead.car_price_cop} COP

Reglas por intención:
- NOT_INTERESTED → agradece y cierra suave.
- FOLLOW_UP → ofrece enviar info o llamar luego.
- INTERESTED → recomienda un servicio y pregunta día/hora.
- NEUTRAL → haz pregunta simple y avanza.

Servicios:
1) Premium: lavado + polichado + partes negras + 20 fotos (350k + IVA)
2) Intermedia: lavado + 20 fotos (200k + IVA)
3) Económica: solo fotos (100k + IVA)
"""

    history_text = (
        "Historial breve:\n"
        f"{history_block if history_block else '[Sin mensajes previos]'}\n"
    )

    user_block = (
        f"Mensaje del cliente: \"{user_text}\"\n"
        f"Intención detectada: {intent}\n\n"
        "Responde según las reglas anteriores con máximo 3 oraciones cortas."
    )

    full_prompt = system_block + "\n" + history_text + "\n" + user_block

    response = reply_model.generate_content(
        full_prompt,
    )

    return (response.text or "").strip()