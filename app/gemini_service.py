import json
import re
from typing import List, Dict

import google.generativeai as genai
from faster_whisper import WhisperModel

from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

from app.models import Lead

# -------------------------------------------------------------------
# GLOBAL MODELS
# -------------------------------------------------------------------

# ---------- Faster Whisper (local STT) ----------
whisper_model = WhisperModel(
    "base",
    device="cpu",
    compute_type="int8"
)

# ---------- Local Intent Classifier (BETO Sentiment) ----------
intent_tokenizer = AutoTokenizer.from_pretrained("finiteautomata/beto-sentiment-analysis")
intent_model_fast = AutoModelForSequenceClassification.from_pretrained(
    "finiteautomata/beto-sentiment-analysis"
)
label_map = {0: "NEG", 1: "NEU", 2: "POS"}

# ---------- Gemini for reply generation ONLY ----------
reply_model = genai.GenerativeModel("models/gemini-flash-latest")


# -------------------------------------------------------------------
# FAST LOCAL INTENT CLASSIFICATION
# -------------------------------------------------------------------
def classify_intent_fast(text: str) -> str:
    """
    Super fast Spanish intent classifier (5–10 ms).
    Maps sentiment → (INTERESTED, NOT_INTERESTED, FOLLOW_UP, NEUTRAL)
    """

    inputs = intent_tokenizer(text, return_tensors="pt", truncation=True)
    with torch.no_grad():
        logits = intent_model_fast(**inputs).logits

    pred_id = int(torch.argmax(logits))
    sentiment = label_map[pred_id]  # NEG, NEU, POS

    low = text.lower()

    # ------- Mapping rules -------
    if sentiment == "NEG" or any(p in low for p in [
        "no quiero", "no me interesa", "caro", "no gracias", "no por ahora"
    ]):
        return "NOT_INTERESTED"

    if any(p in low for p in [
        "luego", "más tarde", "mas tarde", "después", "despues"
    ]):
        return "FOLLOW_UP"

    if sentiment == "POS" or any(p in low for p in [
        "interesado", "interesa", "cuéntame", "cuentame", "quiero saber"
    ]):
        return "INTERESTED"

    return "NEUTRAL"


# -------------------------------------------------------------------
# TRANSCRIBE + INTENT
# -------------------------------------------------------------------
def transcribe_and_analyze(file_path: str, mime_type: str = "audio/webm"):
    """
    Transcribe audio using Faster Whisper + classify intent locally.
    """

    print("🎤 Iniciando transcripción con Faster Whisper...")

    segments, info = whisper_model.transcribe(
        file_path,
        language="es",
        beam_size=5,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 300},
    )

    print("🌎 Idioma detectado:", info.language)
    print("📊 Probabilidad idioma:", info.language_probability)

    full_text = []
    print("🔎 Segmentos detectados:")
    for seg in segments:
        print(f"  🟦 [{seg.start:.2f}s → {seg.end:.2f}s] {seg.text}")
        full_text.append(seg.text)

    transcript = " ".join(full_text).strip()
    print("📝 TRANSCRIPCIÓN FINAL:", transcript or "<vacía>")

    if not transcript:
        print("⚠️ No se detectó texto. Intent = NEUTRAL")
        return {"transcript": "", "intent": "NEUTRAL"}

    # ---------- LOCAL INTENT ----------
    print("⚡ Clasificando intención localmente...")
    intent = classify_intent_fast(transcript)
    print("🔮 INTENCIÓN DETECTADA:", intent)

    return {
        "transcript": transcript,
        "intent": intent,
    }


# -------------------------------------------------------------------
# BUILD RESPONSE (GEMINI — SHORT ANSWERS)
# -------------------------------------------------------------------
def build_response(
    lead: Lead,
    user_text: str,
    intent: str,
    history: List[Dict[str, str]],
) -> str:

    history_block = ""
    for turn in history[-2:]:
        history_block += f"Usuario: {turn.get('user')}\nAgente: {turn.get('agent')}\n\n"

    print("🧵 HISTORY BLOCK SENT TO GEMINI:")
    print(history_block or "[Sin mensajes previos]")

    system_block = f"""
Eres un asesor comercial colombiano, profesional y cercano.
Respuestas SIEMPRE cortas (máximo 3 oraciones, 12 palabras c/u).
Nunca suenes robótico. Habla como vendedor experto.

Cliente: {lead.name}
Vehículo: {lead.car_name} {lead.car_model}
Precio estimado: {lead.car_price_cop} COP

Reglas por intención:
- NOT_INTERESTED:
    • Intenta UNA sola vez más con una respuesta empática, breve y sin presión.
    • Si vuelve a mostrar desinterés, agradece y cierra suavemente.
- FOLLOW_UP:
    • Ofrece enviar información o llamar luego.
- INTERESTED:
    • Recomienda el servicio adecuado y pregunta fecha/hora.
    • NO pidas dirección al cliente.
    • En su lugar, recomienda una sede imaginaria: Sede Norte, Sede Centro o Sede Sur.
- NEUTRAL:
    • Haz una pregunta simple para avanzar la conversación.

Regla importante:
- NO preguntes por dirección del cliente.
- Si necesitas ofrecer lugares, usa únicamente:
    • Sede Norte
    • Sede Centro
    • Sede Sur
  Nunca menciones direcciones reales ni detalles logísticos.

Servicios:
1) Premium: lavado + polichado + partes negras + 20 fotos (350k + IVA)
2) Intermedia: lavado + 20 fotos (200k + IVA)
3) Económica: solo fotos (100k + IVA)
"""

    history_text = f"Historial breve:\n{history_block or '[Sin mensajes previos]'}\n"

    user_block = (
        f"Mensaje del cliente: \"{user_text}\"\n"
        f"Intención detectada: {intent}\n\n"
        "Responde con máximo 3 oraciones cortas."
    )

    full_prompt = system_block + "\n" + history_text + "\n" + user_block

    response = reply_model.generate_content(
        full_prompt,
    )

    text = (response.text or "").strip()
    print("🤖 RESPUESTA GEMINI:", text)
    return text