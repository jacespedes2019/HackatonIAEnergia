import json
import google.generativeai as genai
from app.models import Lead
from typing import List, Dict

# All comments in English.

def transcribe_and_analyze(file_path: str, mime_type: str = "audio/webm"):
    """
    Transcribe audio and classify user intent in ONE call using Gemini Flash.
    Returns: { "transcript": str, "intent": str }
    """

    model = genai.GenerativeModel("models/gemini-flash-latest")

    with open(file_path, "rb") as f:
        audio_bytes = f.read()

    audio_part = {
        "mime_type": mime_type,
        "data": audio_bytes,
    }

    prompt = """
Eres un asistente que opera en una llamada comercial.

Devuelve UN JSON PURO, sin markdown, sin ``` ni bloques de código.

Formato EXACTO:
{
 "transcript": "...",
 "intent": "NOT_INTERESTED" | "INTERESTED" | "FOLLOW_UP" | "NEUTRAL"
}

REGLAS:
- "transcript": transcribe EXACTAMENTE en español lo que dice la persona.
- "intent": clasifica UNA sola intención según:

NOT_INTERESTED:
  rechazo directo, objeción fuerte, "no quiero", "no me interesa", "muy caro".

INTERESTED:
  preguntas activas, interés explícito, curiosidad real, disposición a avanzar.

FOLLOW_UP:
  "hablamos luego", "llámame después", "más tarde", "en otro momento".

NEUTRAL:
  respuestas ambiguas, ruido, frases no relacionadas o sin intención clara.

NO EXPLIQUES.
NO USES ``` NI BLOQUES DE CÓDIGO.
NO AGREGUES TEXTO EXTRA.
SOLO RESPONDE EL JSON.
"""

    response = model.generate_content([audio_part, prompt])
    raw = (response.text or "").strip()

    # --- helper to robustly extract JSON from raw text ---
    def parse_json_from_gemini(text: str) -> dict:
        """Try several strategies to get a valid JSON object from Gemini output."""
        # 1) Direct attempt
        try:
            return json.loads(text)
        except Exception:
            pass

        # 2) Remove markdown fences if present
        cleaned = text.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(cleaned)
        except Exception:
            pass

        # 3) Extract first {...} block with regex
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            candidate = match.group(0)
            try:
                return json.loads(candidate)
            except Exception:
                pass

        # If everything fails, raise
        raise ValueError("Could not parse JSON from Gemini response")

    try:
        data = parse_json_from_gemini(raw)
        transcript = str(data.get("transcript", "")).strip()
        intent = str(data.get("intent", "NEUTRAL")).strip().upper()
    except Exception:
        # Fallback: treat full text as transcript, neutral intent
        transcript = raw
        intent = "NEUTRAL"

    return {
        "transcript": transcript,
        "intent": intent,
    }


def build_response(
    lead: Lead,
    user_text: str,
    intent: str,
    history: List[Dict[str, str]],
) -> str:
    """
    Use Gemini to generate a Spanish response for a sales call
    about detailed car washing and professional photography,
    taking into account the previous turns in the conversation (history).
    """
    model = genai.GenerativeModel("models/gemini-flash-latest")

    # Build conversation history block (only last 5 turns to keep prompt small)
    history_block = ""
    for turn in history[-5:]:
        user_prev = turn.get("user", "")
        agent_prev = turn.get("agent", "")
        history_block += f"Usuario: {user_prev}\nAgente: {agent_prev}\n\n"
        
    # Debug: show what we are sending as history to the model
    print("🧵 HISTORY BLOCK SENT TO GEMINI:")
    print(history_block if history_block else "[Sin mensajes previos]")

    # System instructions with personalized lead data
    system_block = f"""
Eres un asesor comercial experto en Colombia. Vendes servicios de lavado detallado y fotografía profesional
para que las personas vendan su carro más rápido y sin bajar el precio.

TU META:
- Entender la situación del cliente.
- Recomendar solo 1 o 2 servicios adecuados (no los 3).
- Resolver dudas y objeciones de forma amable y breve.
- Guiar hacia el agendamiento del servicio.
- Si no compra, cerrar amable dejando la puerta abierta.

TONO:
- Español latino, cercano, profesional y natural.
- Respuestas cortas (máximo 3 oraciones).
- No suenes robótico; tono humano de vendedor experto.
- Muestra empatía y avanza la conversación sin presionar.

CONTEXTO PERSONALIZADO:
- Cliente: {lead.name}
- Vehículo: {lead.car_name} {lead.car_model}
- Precio estimado: {lead.car_price_cop} COP

SERVICIOS (elige estratégicamente cuál mencionar según lo que diga):
1. Opción Premium (cliente muy interesado):
   Lavado detallado + polichado + partes negras + 20 fotos profesionales.
   Duración: 3 horas. Costo: 350.000 + IVA.

2. Opción Intermedia (interés medio):
   Lavado detallado + 20 fotos profesionales.
   Duración: 2 horas. Costo: 200.000 + IVA.

3. Opción Económica (cliente dudoso o con poco presupuesto):
   Solo sesión de 20 fotos profesionales a domicilio.
   Duración: 1 hora. Costo: 100.000 + IVA.

REGLAS:
- No menciones las tres opciones juntas.
- Ofrece máximo dos.
- Si el cliente está negativo: responde con respeto, agradece y no presiones.
- Si muestra interés: lleva la conversación hacia agendar día, hora y sede.
- Si pregunta precios o detalles, responde de forma clara y concisa.
- Usa el mensaje base cuando sea útil: “El 80% de nuestros clientes vende su carro en menos de un mes sin bajar el precio”.

INTENCIÓN DETECTADA:
- NOT_INTERESTED → Respeta, agradece y cierra suave.
- FOLLOW_UP → Ofrece enviar info o agendar más tarde.
- INTERESTED → Recomienda el servicio adecuado y pregunta por fecha/hora.
- NEUTRAL → Haz preguntas simples y dirige la conversación.

Responde de forma natural y coherente con el mensaje del cliente.
"""

    history_text = (
        "Historial de la conversación hasta ahora (usuario vs agente):\n"
        f"{history_block if history_block else '[Sin mensajes previos]'}\n"
    )

    user_block = (
        f"Mensaje actual del usuario: \"{user_text}\"\n"
        f"Intención detectada (clasificación interna): {intent}\n\n"
        "Responde de forma coherente con el historial anterior y el mensaje actual, "
        "siguiendo las reglas y objetivos anteriores. Mantén las respuestas cortas, "
        "conversacionales y naturales, como un vendedor experto que habla por teléfono."
    )

    full_prompt = system_block + "\n" + history_text + "\n" + user_block

    response = model.generate_content(full_prompt)
    return (response.text or "").strip()