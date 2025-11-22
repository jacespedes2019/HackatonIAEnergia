import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from app.database import get_lead_by_phone
from app.elevenlabs_service import generate_tts

from app.config import AUDIO_DIR
from app.ws_routes import router as ws_router

# All comments in English.

app = FastAPI(title="Domu Walkie-Talkie Voice Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register WebSocket routes
app.include_router(ws_router, prefix="/ws")


@app.get("/health")
def health():
    """Simple healthcheck endpoint."""
    return {"status": "ok"}


@app.get("/audio/{filename}")
def get_audio(filename: str):
    """
    Serve ElevenLabs-generated audio files so the frontend
    can play them via <audio src="...">.
    """
    file_path = os.path.join(AUDIO_DIR, filename)
    if not os.path.exists(file_path):
        return PlainTextResponse("Audio not found", status_code=404)
    return FileResponse(file_path, media_type="audio/mpeg")

@app.get("/intro")
def intro(phone: str = Query(..., description="Lead phone number")):
    """
    Generate an initial intro message TTS for a given phone number.
    """
    # comments in English only
    try:
        lead = get_lead_by_phone(phone)
    except Exception:
        raise HTTPException(status_code=404, detail="Lead not found for this phone")

    text = (
        f"Hola {lead.name}, ¿cómo estás? Vi tu carro en TuCarro y quería contarte "
        "que el 80% de nuestros clientes vende en menos de un mes y sin bajar el precio "
        "gracias a nuestro lavado detallado y fotos profesionales. "
        "¿Estás interesado en el servicio?"
    )

    audio_url = generate_tts(text, prefix=f"intro_{lead.id}")

    return {
        "text": text,
        "audioUrl": audio_url,
        "leadId": lead.id,
        "leadName": lead.name,
    }
    
    
    # en app/main.py
from app.database import get_next_pending_lead
from app.config import supabase_client

@app.get("/debug/leads")
def debug_leads():
    # comments in English only
    resp = (
        supabase_client.table("Lead")
        .select("*")
        .limit(5)
        .execute()
    )
    return resp.data