# Real-Time Speech Transcription and Meeting Summarization

A web application that performs **real-time multilingual speech transcription** using **faster-whisper** and generates an **English meeting summary** using **Google Gemini**. It supports mixed Urdu, Hindi, Punjabi, and English conversations through a simple browser interface.

## Table of Contents
- Features
- Architecture
- Tech Stack
- Setup
- Usage
- Design Decisions
- Limitations

## Features
- Live microphone transcription
- Mixed-language speech support
- Automatic language detection
- Real-time transcript updates via WebSockets
- English meeting summaries with Gemini
- Automatic reconnect on connection loss

## Architecture
1. Browser records audio with `MediaRecorder`.
2. Audio is sent in 8-second chunks over WebSocket.
3. FastAPI receives each chunk.
4. `faster-whisper` transcribes locally.
5. Partial transcripts stream back to the browser.
6. When the session ends, the full transcript is summarized with Gemini and returned.

## Tech Stack
- FastAPI
- WebSockets
- faster-whisper
- Google Gemini (`gemini-2.0-flash`)
- HTML/CSS/JavaScript

## Setup

```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
```

Add your Gemini API key to `.env`:

```text
GEMINI_API_KEY=YOUR_API_KEY
```

Run the backend:

```bash
uvicorn server:app --reload --port 8000
```

Open `frontend/index.html` directly or serve it:

```bash
cd frontend
python -m http.server 5500
```

Visit `http://localhost:5500`, allow microphone access, then start a session.

## Usage
1. Start a session.
2. Speak naturally in one or more supported languages.
3. Watch the live transcript.
4. End the session to receive an English summary.

## Design Decisions
- **Server-side transcription** for better multilingual accuracy.
- **Local faster-whisper** to avoid transcription API costs.
- **8-second chunking** ensures valid audio files for Whisper.
- **Gemini Flash** provides fast, low-cost summarization.
- **Automatic language detection** supports code-switching.

## Limitations
- Words may split across chunk boundaries.
- Uses the Whisper **tiny** model for speed over maximum accuracy.
- No speaker diarization or timestamps.
- No transcript export.
- Silent audio is still processed.

## Future Improvements
- Streaming PCM audio
- Silence detection
- Speaker diarization
- Transcript export
- Larger Whisper models for improved accuracy

## License
MIT
