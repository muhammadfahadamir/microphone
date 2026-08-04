import os
import json
import asyncio
import tempfile

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from faster_whisper import WhisperModel
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
gemini_model = genai.GenerativeModel("gemini-3.6-flash")

# Loads once at startup. "tiny" is smaller/faster to download; swap to
# "small" or "medium" later for better accuracy once things are working.
whisper_model = WhisperModel("small", device="cpu", compute_type="int8")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SUMMARY_TIMEOUT_SECONDS = 45


def transcribe_chunk(audio_bytes: bytes) -> str:
    """Transcribe one self-contained audio chunk locally with faster-whisper."""
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
        f.write(audio_bytes)
        temp_path = f.name
    try:
        segments, _ = whisper_model.transcribe(temp_path, language=None)
        return " ".join(segment.text.strip() for segment in segments).strip()
    finally:
        os.unlink(temp_path)


def summarize_blocking(full_transcript: str) -> str:
    """Blocking call to Gemini. Always run this inside a thread, never
    directly in the async event loop, or one slow network call freezes the
    whole server (including reading new websocket messages)."""
    prompt = (
        "You are given the transcript of a live spoken session. The speaker may "
        "have used Urdu, Hindi, Punjabi, English, or a mix, sometimes switching "
        "languages mid-sentence.\n\n"
        "Write a clear ENGLISH summary of the whole session: main topics, key "
        "points, and any decisions or action items. Someone who was not in the "
        "room should be able to understand it.\n\n"
        f"TRANSCRIPT:\n{full_transcript}"
    )
    response = gemini_model.generate_content(prompt)
    return response.text.strip()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    transcript_parts = []
    try:
        while True:
            message = await websocket.receive()

            # Binary audio chunk from the browser
            if message.get("bytes") is not None:
                audio_bytes = message["bytes"]
                if len(audio_bytes) < 1000:
                    continue
                try:
                    text = await asyncio.to_thread(transcribe_chunk, audio_bytes)
                except Exception as e:
                    await websocket.send_json({"type": "error", "message": str(e)})
                    continue
                if text:
                    transcript_parts.append(text)
                    await websocket.send_json({"type": "partial", "text": text})

            # Text control message from the browser
            elif message.get("text") is not None:
                data = json.loads(message["text"])
                if data.get("type") == "end_session":
                    full_transcript = " ".join(transcript_parts)
                    summary = ""
                    if full_transcript.strip():
                        try:
                            summary = await asyncio.wait_for(
                                asyncio.to_thread(summarize_blocking, full_transcript),
                                timeout=SUMMARY_TIMEOUT_SECONDS,
                            )
                        except asyncio.TimeoutError:
                            summary = (
                                "(Summary timed out after "
                                f"{SUMMARY_TIMEOUT_SECONDS}s — check your internet "
                                "connection to Google's servers and try again.)"
                            )
                        except Exception as e:
                            summary = f"(summary failed: {e})"
                    await websocket.send_json({
                        "type": "final",
                        "transcript": full_transcript,
                        "summary": summary,
                    })
    except WebSocketDisconnect:
        pass