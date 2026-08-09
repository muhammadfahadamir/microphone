# Real-Time Speech Transcription and Meeting Summarization

## Setup and run (clean machine)

1. Install Python 3.10+.
2. `cd backend`
3. `python -m venv venv && source venv/bin/activate` (Windows: `venv\Scripts\activate`)
4. `pip install -r requirements.txt`
5. `cp .env.example .env` and put your real Gemini API key in `.env`
6. `uvicorn server:app --reload --port 8000`
7. Open `frontend/index.html` directly in Chrome (double-click the file, or serve it
   with `python -m http.server 5500` from the `frontend/` folder and visit
   `http://localhost:5500`). Allow microphone access when prompted.
8. Click **Start Session**, speak (mix Urdu/Hindi/Punjabi/English freely), click
   **End Session** when done.

## Architecture: how audio flows from mic to final output

1. **Browser** requests mic access via `getUserMedia`. Three permission states
   (pending / granted / denied) are shown explicitly; a denial disables recording
   but leaves the rest of the page usable.
2. On **Start**, the browser opens a WebSocket to the backend and begins recording
   with `MediaRecorder`. Instead of one continuous stream, the recorder is
   **restarted every few seconds**, so each blob it produces is a complete,
   independently-decodable `.webm/opus` file (a single MediaRecorder stream only
   has valid headers on its first chunk — later chunks alone aren't decodable by
   Whisper, so restarting sidesteps that).
3. Each blob is sent as **binary data over the WebSocket** to the FastAPI backend.
4. The backend writes the chunk to a temp file and transcribes it locally with
   **faster-whisper** ("small" model), with no forced `language` parameter, so it
   can auto-detect and follow language switches within the session.
5. The transcribed text for that chunk is pushed back to the browser immediately
   as a `partial` WebSocket message and appended to the on-screen transcript live.
6. On **End Session**, the browser sends an `end_session` control message along
   with the full transcript it has accumulated client-side (this matters — see
   the reconnection note below). The backend sends that transcript to **Google
   Gemini** (`gemini-3.6-flash`) with an explicit instruction to summarize in
   English regardless of the source language(s), and returns the summary as a
   `final` message. Transcript and summary render on the same page, no reload.
7. If the WebSocket drops mid-session, the frontend detects `onclose` and
   auto-reconnects, retrying up to 5 times with a visible attempt counter before
   giving up. On successful reconnect it resumes sending new audio chunks.

## Key decisions and tradeoffs

- **Server-side transcription (Option B) over browser-side (Option A):** the
  browser's built-in Web Speech API is unreliable for Urdu/Hindi/Punjabi and
  essentially unusable for mid-sentence code-switching, which this project
  requires. Whisper-family models handle mixed-language, real-world speech
  far better.
- **Local faster-whisper instead of a cloud transcription API:** this avoids
  any per-request API cost and works fully offline after the model is
  downloaded once, at the cost of slower transcription on a normal laptop CPU
  compared to a cloud service.
- **Chunked restart recording instead of one continuous stream:** Whisper
  needs complete audio files, not a raw ongoing stream. Restarting the
  recorder is the simplest way to get complete files while staying close to
  real time. The cost: a word can occasionally be split across a chunk
  boundary, which slightly hurts word-level accuracy right at those boundaries.
- **Google Gemini (gemini-3.6-flash) for summarization:** free tier with no
  billing required, fast, and good enough at instruction-following
  ("summarize in English no matter the input language") for a session-length
  transcript.
- **Client-side transcript as the source of truth for summarization:** the
  backend's own per-connection transcript memory resets on every reconnect,
  so relying on it after a mid-session reconnect would silently drop earlier
  content from the summary. The browser sends its full accumulated transcript
  along with `end_session` specifically to avoid this.
- **No forced `language` param on Whisper:** letting it auto-detect per chunk
  handles language switching better than pinning one language, at a small risk
  of misdetecting very short chunks.

## Known limitations / what I'd do differently with more time

- Chunk-boundary word splitting (see above) — a raw PCM streaming approach via
  `AudioWorklet` with server-side re-buffering would avoid this entirely but is
  more complex to implement correctly.
- Audio captured during a dropped connection, before reconnection completes,
  is not recovered — it was never sent to the server before the drop.
  Reconnection resumes new audio, not the gap itself.
- No speaker diarization or timestamps (both bonus items, not implemented).
- No export button for transcript/summary (bonus item, not implemented).
- Using Whisper's "small" model is a reasonable accuracy/speed middle ground
  on CPU — "medium" or "large" would improve accuracy further at the cost of
  slower per-chunk transcription and a bigger download.

## Sample output

Add your real multilingual run's transcript and summary text here before
submitting (required deliverable #3).