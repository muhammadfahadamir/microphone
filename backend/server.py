import os
import json
import asyncio
import tempfile

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from faster_whisper import WhisperModel
import google.generativeai as genai
from dotenv import load_dotenv


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

genai.configure(api_key=GEMINI_API_KEY)

gemini_model = genai.GenerativeModel(
    "gemini-3.6-flash"
)


# ============================================================
# WHISPER
# ============================================================


#you can change this to small or tiny if the processor is not good 
whisper_model = WhisperModel(
    "medium",
    device="cpu",
    compute_type="int8",
)


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


SUMMARY_TIMEOUT_SECONDS = 45


# ============================================================
# TRANSCRIPTION
# ============================================================

def transcribe_chunk(audio_bytes: bytes) -> str:
    """
    Transcribe one complete WebM/Opus chunk.

    VAD is enabled so silence and background noise are less
    likely to produce garbage transcription.
    """

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            suffix=".webm",
            delete=False,
        ) as f:
            f.write(audio_bytes)
            temp_path = f.name

        segments, _ = whisper_model.transcribe(
            temp_path,

            # Let Whisper detect the language automatically.
            language=None,

            # Ignore sections that are effectively silence.
            vad_filter=True,

            # Make VAD reasonably aggressive against silence.
            vad_parameters={
                "min_silence_duration_ms": 500,
            },

            # Slightly reduce hallucination from noisy audio.
            condition_on_previous_text=False,
        )

        text_parts = []

        for segment in segments:
            text = segment.text.strip()

            if not text:
                continue

            # Ignore punctuation-only hallucinations.
            meaningful = text.strip(
                " .,!?:;'-_\"()[]{}<>/\\|"
            )

            if not meaningful:
                continue

            text_parts.append(text)

        return " ".join(text_parts).strip()

    finally:
        if temp_path:
            try:
                os.unlink(temp_path)
            except FileNotFoundError:
                pass


# ============================================================
# GEMINI SUMMARY
# ============================================================

def summarize_blocking(full_transcript: str) -> str:
    """
    Blocking Gemini request.

    This function is always executed in a worker thread so
    the WebSocket event loop remains responsive.
    """

    prompt = (
        "You are given the transcript of a live spoken session.\n\n"

        "The speaker may use Urdu, Hindi, Punjabi, English, "
        "or a mixture of these languages and may switch "
        "languages during a sentence.\n\n"

        "Write a clear ENGLISH summary of the entire session.\n\n"

        "Include:\n"
        "- Main topics\n"
        "- Important points\n"
        "- Decisions\n"
        "- Action items\n\n"

        "Do not invent information that is not present in "
        "the transcript.\n\n"

        "TRANSCRIPT:\n"
        f"{full_transcript}"
    )

    response = gemini_model.generate_content(prompt)

    return response.text.strip()


# ============================================================
# SAFE WEBSOCKET SEND
# ============================================================

async def safe_send_json(
    websocket: WebSocket,
    data: dict,
) -> bool:

    try:
        await websocket.send_json(data)
        return True

    except (
        WebSocketDisconnect,
        RuntimeError,
    ):
        return False


# ============================================================
# WEBSOCKET ENDPOINT
# ============================================================

@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
):

    await websocket.accept()

    transcript_parts = []

    connected = True

    print("WebSocket session started.")


    try:

        while connected:

            message = await websocket.receive()


            # ====================================================
            # CLIENT DISCONNECTED
            # ====================================================

            if message.get("type") == "websocket.disconnect":
                break


            # ====================================================
            # BINARY AUDIO
            # ====================================================

            if message.get("bytes") is not None:

                audio_bytes = message["bytes"]

                if len(audio_bytes) < 1000:
                    continue

                print(
                    f"Received audio chunk: "
                    f"{len(audio_bytes)} bytes"
                )


                # ------------------------------------------------
                # TRANSCRIBE WITHOUT BLOCKING ASYNC LOOP
                # ------------------------------------------------

                try:

                    text = await asyncio.to_thread(
                        transcribe_chunk,
                        audio_bytes,
                    )

                except Exception as e:

                    print(
                        "Whisper error:",
                        repr(e),
                    )

                    connected = await safe_send_json(
                        websocket,
                        {
                            "type": "error",
                            "message": str(e),
                        },
                    )

                    continue


                if not connected:
                    break


                print(
                    "Transcription:",
                    repr(text),
                )


                # ------------------------------------------------
                # SEND REAL SPEECH ONLY
                # ------------------------------------------------

                if text:

                    transcript_parts.append(text)

                    connected = await safe_send_json(
                        websocket,
                        {
                            "type": "partial",
                            "text": text,
                        },
                    )

                    if not connected:
                        break


            # ====================================================
            # TEXT / CONTROL MESSAGE
            # ====================================================

            elif message.get("text") is not None:

                try:

                    data = json.loads(
                        message["text"]
                    )

                except json.JSONDecodeError:

                    connected = await safe_send_json(
                        websocket,
                        {
                            "type": "error",
                            "message": "Invalid JSON message.",
                        },
                    )

                    continue


                # =================================================
                # HEARTBEAT
                # =================================================

                if data.get("type") == "ping":

                    connected = await safe_send_json(
                        websocket,
                        {
                            "type": "pong",
                        },
                    )

                    continue


                # =================================================
                # END SESSION
                # =================================================

                if data.get("type") == "end_session":

                    print(
                        "End session received."
                    )


                    # ------------------------------------------------
                    # Prefer the complete browser transcript.
                    #
                    # This is important if the browser had to
                    # reconnect during the session.
                    # ------------------------------------------------

                    client_transcript = data.get(
                        "transcript"
                    )


                    if (
                        isinstance(
                            client_transcript,
                            str,
                        )
                        and client_transcript.strip()
                    ):

                        full_transcript = (
                            client_transcript.strip()
                        )

                    else:

                        full_transcript = " ".join(
                            transcript_parts
                        ).strip()


                    # ------------------------------------------------
                    # SUMMARY
                    # ------------------------------------------------

                    summary = ""

                    if full_transcript:

                        print(
                            "Generating Gemini summary..."
                        )

                        try:

                            summary = await asyncio.wait_for(
                                asyncio.to_thread(
                                    summarize_blocking,
                                    full_transcript,
                                ),
                                timeout=SUMMARY_TIMEOUT_SECONDS,
                            )

                        except asyncio.TimeoutError:

                            summary = (
                                "Summary timed out after "
                                f"{SUMMARY_TIMEOUT_SECONDS} seconds."
                            )

                        except Exception as e:

                            print(
                                "Summary error:",
                                repr(e),
                            )

                            summary = (
                                f"Summary failed: {e}"
                            )

                    else:

                        summary = (
                            "No speech was detected."
                        )


                    # ------------------------------------------------
                    # FINAL RESULT
                    # ------------------------------------------------

                    await safe_send_json(
                        websocket,
                        {
                            "type": "final",
                            "transcript": full_transcript,
                            "summary": summary,
                        },
                    )


                    print(
                        "Final result sent."
                    )


                    # Session finished.
                    break


    except WebSocketDisconnect:

        connected = False

        print(
            "WebSocket client disconnected."
        )


    except RuntimeError as e:

        connected = False

        print(
            "WebSocket runtime error:",
            repr(e),
        )


    except Exception as e:

        connected = False

        print(
            "WebSocket error:",
            repr(e),
        )


    finally:

        print(
            "WebSocket session ended."
        )