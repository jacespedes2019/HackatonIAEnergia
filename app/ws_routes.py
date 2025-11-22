import os
import tempfile
from typing import List, Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.logger import logger

from app.models import Lead
from app.gemini_service import transcribe_and_analyze, build_response
from app.sentiment import analyze_intent
from app.elevenlabs_service import generate_tts
from app.database import get_lead_by_id
from app.conversation_store import get_history, append_turn
import time

router = APIRouter()


def get_demo_lead() -> Lead:
    """Return a static demo lead, no database needed."""
    return Lead(
        name="Carlos Pérez",
        car_model="Sedán 2022",
        car_name="Domu Sedan X",
        car_price_cop=75_000_000,
    )



@router.websocket("/voice")
async def voice_websocket(ws: WebSocket):
    """
    WebSocket with context:
    - Receives ?lead_id=...
    - Uses global in-memory history per lead_id.
    """
    await ws.accept()

    lead_id_param = ws.query_params.get("lead_id")
    if lead_id_param:
        try:
            lead = get_lead_by_id(lead_id_param)  # UUID in DB
        except Exception:
            lead = get_demo_lead()
    else:
        lead = get_demo_lead()

    # This key will be used to store and retrieve conversation history
    lead_key = str(lead.id)
    print("🔌 WebSocket iniciado con lead:", lead.name, "ID:", lead_key)

    try:
        while True:
            try:
                audio_bytes = await ws.receive_bytes()
            except WebSocketDisconnect:
                print("❌ Cliente desconectado mientras enviaba audio")
                break

            # Save incoming audio to a temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            try:
                t0 = time.perf_counter()

                # 1) STT + intent
                analysis = transcribe_and_analyze(tmp_path)
                user_text = analysis["transcript"]
                intent = analysis["intent"]
                print({"transcript": user_text, "intent": intent})

                # 2) Get current history for this lead
                history = get_history(lead_key)

                # Debug: what we send as history
                history_block = ""
                for turn in history[-5:]:
                    history_block += (
                        f"Usuario: {turn.get('user')}\n"
                        f"Agente: {turn.get('agent')}\n\n"
                    )
                print("🧵 HISTORY BLOCK SENT TO GEMINI:")
                print(history_block if history_block else "[Sin mensajes previos]")

                # 3) Build response with context
                t_resp = time.perf_counter()
                reply_text = build_response(lead, user_text, intent, history)
                resp_ms = (time.perf_counter() - t_resp) * 1000.0

                # 4) TTS
                t_tts = time.perf_counter()
                audio_url = generate_tts(reply_text, prefix=f"ws_reply_{lead.id}")
                tts_ms = (time.perf_counter() - t_tts) * 1000.0

                total_ms = (time.perf_counter() - t0) * 1000.0
                print(
                    f"📊 PERF → RESP={resp_ms:.1f}ms | "
                    f"TTS={tts_ms:.1f}ms | TOTAL={total_ms:.1f}ms"
                )

                # 5) Append new turn to global history
                append_turn(lead_key, user_text, reply_text)
                new_history = get_history(lead_key)
                print("📚 History length:", len(new_history))
                for i, turn in enumerate(new_history[-3:], start=1):
                    print(f"  Turn {len(new_history)-3+i}:")
                    print("    Usuario:", turn.get("user"))
                    print("    Agente:", turn.get("agent"))

                # 6) Send reply to frontend
                await ws.send_json({
                    "type": "reply",
                    "userText": user_text,
                    "intent": intent,
                    "replyText": reply_text,
                    "audioUrl": audio_url,
                })

            except Exception as e:
                print("💥 ERROR procesando audio:", e)
                await ws.send_json({
                    "type": "error",
                    "message": "Error procesando el audio en el servidor",
                    "detail": str(e),
                })
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

    except WebSocketDisconnect:
        print("🔌 Cliente desconectado")