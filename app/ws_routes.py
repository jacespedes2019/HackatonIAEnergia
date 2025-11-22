import os
import tempfile

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.logger import logger

from app.models import Lead
from app.gemini_service import transcribe_audio, build_response
from app.sentiment import analyze_intent
from app.elevenlabs_service import generate_tts

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
    Walkie-talkie style WebSocket:
    - Receives one audio blob (binary) per turn.
    - Transcribes with Gemini.
    - Analyzes intent.
    - Generates reply text with Gemini.
    - Generates TTS with ElevenLabs.
    - Sends JSON with userText, intent, replyText, audioUrl.
    """
    await ws.accept()
    demo_lead = get_demo_lead()

    try:
        while True:
            try:
                audio_bytes = await ws.receive_bytes()
            except WebSocketDisconnect:
                logger.info("Client disconnected while waiting for audio bytes")
                break

            # Save temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            try:
                # 1) Transcribe audio
                user_text = transcribe_audio(tmp_path, mime_type="audio/webm")

                # 2) Analyze intent
                intent = analyze_intent(user_text)

                # 3) Build reply text
                reply_text = build_response(demo_lead, user_text, intent)

                # 4) Generate TTS
                audio_url = generate_tts(reply_text, prefix="ws_reply")

                # 5) Send reply
                await ws.send_json({
                    "type": "reply",
                    "userText": user_text,
                    "intent": intent,
                    "replyText": reply_text,
                    "audioUrl": audio_url,
                })

            except Exception as e:
                # Log full error on server
                logger.exception(f"Error processing audio: {e}")
                # Send error info to client instead of silently closing
                await ws.send_json({
                    "type": "error",
                    "message": "Error procesando el audio en el servidor",
                    "detail": str(e),
                })

            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")