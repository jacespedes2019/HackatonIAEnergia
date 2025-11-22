import os
from fastapi import FastAPI
from fastapi.responses import FileResponse, PlainTextResponse

from app.config import AUDIO_DIR
from app.ws_routes import router as ws_router

# All comments in English.

app = FastAPI(title="Domu Walkie-Talkie Voice Backend")

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