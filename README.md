# Real-Time Speech Transcription and Meeting Summarization

## 1. Setup and Execution

Follow the steps below to install and run the application on a clean machine.

### Prerequisites

* Python 3.10 or later
* A working microphone
* Internet access for Gemini-based summarization
* A valid Google Gemini API key

### Installation

1. Navigate to the backend directory:

```bash
cd backend
```

2. Create and activate a Python virtual environment:

**Linux/macOS:**

```bash
python -m venv venv
source venv/bin/activate
```

**Windows:**

```bash
python -m venv venv
venv\Scripts\activate
```

3. Install the required dependencies:

```bash
pip install -r requirements.txt
```

4. Create the environment configuration file.

Copy `.env.example` to `.env`:

**Linux/macOS:**

```bash
cp .env.example .env
```

**Windows:**

```cmd
copy .env.example .env
```

Add the actual Gemini API key to the `.env` file.

5. Start the FastAPI backend:

```bash
uvicorn server:app --reload --port 8000
```

6. Open the frontend.

The frontend can either be opened directly in Chrome by opening `frontend/index.html`, or served using Python:

```bash
cd frontend
python -m http.server 5500
```

Then open:

```text
http://localhost:5500
```

7. Allow microphone access when prompted by the browser.

8. Click **Start Session**, speak normally, and freely switch between Urdu, Hindi, Punjabi, and English.

9. Click **End Session** when the session is complete. The final transcript and English summary will then be displayed on the same page.

---

## 2. System Architecture

The application consists of a browser-based frontend and a FastAPI backend connected through a WebSocket.

### Audio-to-Output Pipeline

1. **Microphone Access**

   The browser requests microphone access using the `getUserMedia` API. The interface explicitly displays the microphone permission state, including pending, granted, and denied states. If permission is denied, recording remains disabled while the remainder of the interface remains accessible.

2. **Audio Recording**

   When the user selects **Start Session**, the frontend establishes a WebSocket connection with the backend and begins recording audio using the browser's `MediaRecorder` API.

   Instead of maintaining one continuous recording, the recorder is periodically restarted. This produces complete, independently decodable `.webm/opus` audio files that can be processed individually by the transcription backend.

3. **WebSocket Transmission**

   Each completed audio chunk is transmitted to the FastAPI backend as binary data through the WebSocket connection.

4. **Local Speech Recognition**

   The backend temporarily stores each received audio chunk and processes it using **faster-whisper** with the `small` model.

   No fixed language parameter is supplied to Whisper. This allows the model to automatically detect the spoken language and handle sessions containing Urdu, Hindi, Punjabi, English, or combinations of these languages.

5. **Live Transcript Updates**

   After processing each audio chunk, the backend sends the recognized text to the browser through a WebSocket `partial` message.

   The frontend appends each received transcription to the existing transcript, allowing the user to observe the transcription during the session without reloading the page.

6. **Session Completion and Summarization**

   When the user selects **End Session**, the frontend sends an `end_session` control message containing the complete transcript accumulated by the browser.

   The backend sends this transcript to **Google Gemini (`gemini-3.6-flash`)** with instructions to generate a clear English summary regardless of the language or combination of languages used during the session.

   The backend then returns both the final transcript and generated summary to the frontend through a `final` WebSocket message.

7. **Connection Recovery**

   If the WebSocket connection is unexpectedly interrupted during a session, the frontend detects the connection closure and attempts to reconnect automatically.

   The system performs up to five reconnection attempts and displays the current attempt number to the user. Once the connection is successfully restored, audio recording and transmission resume.

---

## 3. Key Design Decisions and Trade-offs

### 3.1 Server-Side Transcription

The application uses server-side transcription rather than the browser's built-in Web Speech API.

This decision was made because browser-based speech recognition is less suitable for the project's requirement to handle Urdu, Hindi, Punjabi, English, and mid-sentence language switching.

The Whisper model family provides more appropriate multilingual speech recognition for this use case.

### 3.2 Local `faster-whisper` Transcription

Speech recognition is performed locally using `faster-whisper` rather than a cloud-based speech-to-text service.

**Advantages:**

* No per-request transcription cost
* Speech data does not need to be sent to a third-party transcription service
* Operates offline after the Whisper model has been downloaded
* Provides multilingual speech recognition

**Trade-off:**

* Processing speed depends on the available local CPU/GPU hardware
* CPU-based transcription can introduce additional latency compared with cloud-based services or dedicated GPU hardware

### 3.3 Restarted Chunk-Based Recording

The frontend periodically restarts the `MediaRecorder` instead of relying on one continuous recording stream.

This approach produces complete `.webm/opus` files that can be independently processed by the backend.

The primary advantage is implementation simplicity while maintaining near-real-time transcription.

The primary limitation is that speech may occasionally cross a chunk boundary, which can affect recognition accuracy at the boundary between two chunks.

### 3.4 Google Gemini for Summarization

The application uses **Google Gemini (`gemini-3.6-flash`)** to generate the final session summary.

The model receives the accumulated transcript and is instructed to produce an English summary containing the main topics, important points, decisions, and action items.

The summarization process is performed after the recording session has ended.

### 3.5 Client-Side Transcript as the Source of Truth

The browser maintains the complete accumulated transcript and sends it to the backend when the session ends.

This is important because the backend maintains transcript data per WebSocket connection. If the connection is interrupted and subsequently re-established, relying exclusively on the backend's in-memory transcript would risk losing content from the earlier connection.

By maintaining the transcript on the client, previously transcribed content can remain available across reconnection events.

### 3.6 Automatic Language Detection

The `language` parameter is intentionally not forced when calling Whisper.

This allows the model to automatically identify the language present in each audio chunk and better accommodate multilingual sessions in which the speaker changes languages during the conversation.

The trade-off is that very short or unclear audio segments may occasionally be misclassified.

---

## 4. Known Limitations

### 4.1 Chunk Boundary Recognition

Because the system processes independently recorded audio chunks, a word or sentence may occasionally cross a chunk boundary.

This can result in reduced recognition accuracy around the boundary.

A future implementation could use an `AudioWorklet` with raw PCM audio and server-side buffering to provide a more continuous streaming architecture.

### 4.2 Audio During Connection Loss

Audio captured while the WebSocket connection is unavailable cannot be recovered because it has not yet been transmitted to the backend.

The automatic reconnection mechanism resumes transmission after the connection is restored, but it does not recover audio recorded during the interruption.

### 4.3 Speaker Identification

The current implementation does not provide speaker diarization.

Consequently, the system produces a single combined transcript rather than identifying individual speakers.

### 4.4 Timestamps

The current transcript does not include word-level or segment-level timestamps.

### 4.5 Export Functionality

The current interface does not provide dedicated export functionality for saving the transcript or summary as a file.

### 4.6 Model Performance

The `small` Whisper model provides a practical balance between recognition accuracy and processing requirements on a CPU-based system.

Larger models such as `medium` or `large` may improve recognition accuracy, but they require substantially more computational resources and can increase transcription latency.

---

## 5. Future Improvements

Potential improvements to a future version include:

* Continuous audio streaming using `AudioWorklet`
* Server-side audio buffering
* Improved handling of chunk boundaries
* Recovery of audio captured during temporary connection interruptions
* Speaker diarization
* Word-level timestamps
* Transcript and summary export functionality
* GPU-accelerated Whisper inference
* Further optimization of real-time transcription latency

---

## 6. Sample Output
The transcript and summary generated during an actual multilingual test session.


### Sample Transcript

> Hello, this is Fahad Amir speaking. This is the live speech and transcription summary test number 21.
 In this test I am trying to understand the way computers communicate 
- with each other it is quite hard and very difficult type of task 
but I'm trying to understand it मगर जहान ن
ظر آ رہا ہے یہ بہت اچھا کام کر رہا ہے

### Sample Summary

>Here is an English summary of the session:

### **Main Topics**
* Live speech and transcription summary test number 21.
* Understanding how computers communicate with each other.

### **Important Points**
* The speaker, Fahad Amir, is conducting live speech and transcription summary test number 21.
* He noted that learning how computers communicate with each other is a very hard and difficult task, but he is attempting to understand it.
* Switching to Urdu/Hindi at the end, he remarked that, as far as can be seen, it (the system/process) is working very well.

### **Decisions**
* *None mentioned in the transcript.*

### **Action Items**
* *None mentioned in the transcript.*

The sample demonstrate the system's ability to process multilingual speech containing Urdu, Hindi, Punjabi, English, or combinations of these languages and subsequently generate an English summary.
