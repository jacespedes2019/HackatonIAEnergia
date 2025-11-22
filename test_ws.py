# comments in English only

import asyncio
import json
import websockets

AUDIO_FILE = "test.webm"  # path to your test audio file

async def main():
    uri = "ws://localhost:8000/ws/voice"

    async with websockets.connect(uri) as ws:
        print("Connected to WebSocket")

        # 1) Read local audio file as bytes
        with open(AUDIO_FILE, "rb") as f:
            audio_bytes = f.read()

        # 2) Send raw binary audio to the backend
        await ws.send(audio_bytes)
        print("Audio sent, waiting for reply...")

        # 3) Wait for JSON reply
        msg = await ws.recv()
        data = json.loads(msg)

        print("\n--- Backend reply ---")
        print("User text:", data.get("userText"))
        print("Intent:", data.get("intent"))
        print("Reply text:", data.get("replyText"))
        print("Audio URL:", data.get("audioUrl"))

        # 4) Optional: print full JSON
        # print("Raw:", data)

if __name__ == "__main__":
    asyncio.run(main())