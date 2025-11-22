import asyncio
import io
import json
import wave

import av
import numpy as np
import streamlit as st
import websockets
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration

st.set_page_config(page_title="Domu Voice Agent", page_icon="🎙️")

# ----------- WebRTC config -----------
RTC_CONFIGURATION = RTCConfiguration(
    {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
)

# Global buffer to store audio frames (PCM16 chunks)
# Global buffer to store audio frames (PCM16 chunks)
# We create it only once, even if Streamlit reruns the script.
try:
    captured_frames
except NameError:
    captured_frames = []


# ----------- WebSocket call to backend -----------
async def send_audio_ws(audio_bytes: bytes):
    """Send WAV bytes to the WebSocket backend and return JSON reply."""
    uri = "ws://localhost:8000/ws/voice"
    async with websockets.connect(uri) as ws:
        await ws.send(audio_bytes)
        msg = await ws.recv()
        data = json.loads(msg)
        return data


def frames_to_wav_bytes(frames, sample_rate: int = 48000) -> bytes:
    """Convert a list of PCM16 mono chunks to a valid WAV file in memory."""
    pcm = b"".join(frames)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)       # mono
        wf.setsampwidth(2)       # 2 bytes = int16
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)
    return buf.getvalue()


# ----------- Audio callback -----------
def audio_frame_callback(frame: av.AudioFrame):
    """
    Called on each audio frame from WebRTC.
    We store mono PCM16 bytes in a global buffer.
    """
    global captured_frames

    # frame.to_ndarray() -> shape: (channels, samples)
    data = frame.to_ndarray()
    if data.ndim == 2:
        mono = data.mean(axis=0)
    else:
        mono = data
    pcm16 = mono.astype(np.int16).tobytes()

    captured_frames.append(pcm16)
    # Debug: see frames arriving in terminal
    print("🎤 FRAME RECIBIDO, buffer len:", len(captured_frames))

    return frame


# ----------- UI -----------
st.title("🎙️ Domu Voice Agent — Walkie Talkie Mode")
st.write("Presiona **Start**, habla, y luego haz clic en **Enviar al agente 🚀**.")

if "last_reply" not in st.session_state:
    st.session_state.last_reply = None

st.subheader("🎛️ Captura de audio")

webrtc_ctx = webrtc_streamer(
    key="voice-capture",
    mode=WebRtcMode.SENDONLY,  # solo enviamos audio al backend
    rtc_configuration=RTC_CONFIGURATION,
    media_stream_constraints={"audio": True, "video": False},
    audio_frame_callback=audio_frame_callback,
)

if webrtc_ctx and webrtc_ctx.state.playing:
    st.info("Habla mientras 'Start' está activo para capturar audio.")
else:
    st.info("Pulsa **Start** para comenzar a capturar audio.")


st.subheader("🎧 Datos grabados")

if captured_frames:
    st.success(f"Se han capturado {len(captured_frames)} fragmentos de audio. Listo para enviar.")
else:
    st.warning("No hay audio grabado aún.")


# ----------- Enviar al backend -----------
if st.button("Enviar al agente 🚀"):
    if not captured_frames:
        st.warning("No hay audio grabado aún.")
    else:
        # Convert captured PCM16 frames to WAV
        wav_bytes = frames_to_wav_bytes(captured_frames, sample_rate=48000)

        with st.spinner("Procesando audio con el backend..."):
            try:
                data = asyncio.run(send_audio_ws(wav_bytes))
            except Exception as e:
                st.error(f"Error comunicando con backend: {e}")
                st.stop()

        # Limpiar buffer para el siguiente turno
        captured_frames.clear()
        st.session_state.last_reply = data


# ----------- Mostrar resultados -----------
if st.session_state.last_reply:
    data = st.session_state.last_reply

    if data.get("type") == "error":
        st.error("El backend devolvió un error:")
        st.code(data.get("detail", ""), language="text")
    else:
        st.subheader("🗣️ Transcripción del usuario")
        st.write(data.get("userText", ""))

        st.subheader("🧠 Intención detectada")
        st.code(data.get("intent", ""))

        st.subheader("🤖 Respuesta del agente")
        st.write(data.get("replyText", ""))

        st.subheader("🔊 Audio de la respuesta")
        if data.get("audioUrl"):
            st.audio(data["audioUrl"])
        else:
            st.warning("El backend no devolvió audio.")