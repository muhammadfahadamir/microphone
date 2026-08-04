# Step-by-Step Guide: Build, Run, and Submit This Project
### (Free stack: local Whisper for transcription + Google Gemini for summary)

Follow these in order. Don't skip steps even if they seem obvious.

---

## STEP 1 — Install Python

1. Go to python.org/downloads and download Python 3.11 (any 3.10+ works).
2. Run the installer.
   - **Windows:** tick "Add python.exe to PATH" before clicking Install.
   - **Mac:** run the installer normally.
3. Verify it worked. Open a terminal (Windows: Win key → type `cmd` → Enter.
   Mac: Cmd+Space → type `terminal` → Enter) and run:
   ```
   python --version
   ```
   You should see `Python 3.1x.x`. If Windows gives an error, close and reopen
   the terminal and try again.

---

## STEP 2 — Get a free Gemini API key (no card needed)

1. Go to aistudio.google.com and sign in with any Google account.
2. Click **Get API key** → **Create API key**.
3. Copy it — it starts with `AIza...`. Save it somewhere temporarily (a notes
   app), you'll paste it into the project in Step 6.

This is free — no billing, no card, unlike OpenAI's API.

---

## STEP 3 — Unzip and open the project

1. Unzip `speech-app.zip` somewhere convenient, e.g. `Downloads\speech-app`.
2. In your terminal:
   ```
   cd Downloads\speech-app
   ```
3. Confirm you're in the right place:
   ```
   dir
   ```
   You should see `backend`, `frontend`, `README.md`.

---

## STEP 4 — Set up the backend

1. Move into the backend folder:
   ```
   cd backend
   ```
2. Create a virtual environment:
   ```
   python -m venv venv
   ```
3. Activate it:
   ```
   venv\Scripts\activate
   ```
   (Mac/Linux: `source venv/bin/activate`)
   Your prompt should now start with `(venv)`. You must re-run this activate
   command every time you open a new terminal for this project.
4. Install the required packages:
   ```
   pip install -r requirements.txt --timeout 120
   ```
   This installs FastAPI, faster-whisper (local speech-to-text), and the
   Gemini library. If it times out partway (common on slower/unstable
   connections), just re-run the same command.

---

## STEP 5 — Add your Gemini API key

1. Still in the `backend` folder, copy the example env file:
   ```
   copy .env.example .env
   ```
2. Open it in Notepad:
   ```
   notepad .env
   ```
3. Make the file read exactly (your real key, no quotes, no spaces around
   the `=`, all on one line):
   ```
   GEMINI_API_KEY=AIzaYourRealKeyHere
   ```
4. Save and close.
5. Double check it saved correctly:
   ```
   type .env
   ```
   It should print your real key, not `your_key_here`.

**Common mistake:** don't accidentally delete `GEMINI_API_KEY=` and leave
only the key by itself — the app looks for that exact variable name.

---

## STEP 6 — Run the backend server (first run downloads the Whisper model)

1. Still in `backend`, with `(venv)` active:
   ```
   uvicorn server:app --reload --port 8000
   ```
2. The first time you run this, it automatically downloads the local Whisper
   "tiny" speech-to-text model (~75MB) from Hugging Face. You'll see some
   harmless warnings (about `google.generativeai` deprecation, symlinks on
   Windows) — ignore those, they don't stop anything from working.
3. **This download needs a stable connection.** If it seems stuck, open a
   second terminal and check progress:
   ```
   dir %USERPROFILE%\.cache\huggingface\hub\models--Systran--faster-whisper-tiny\blobs
   ```
   Run it twice, 30 seconds apart — the file size should be growing. If it's
   stuck at 0 bytes both times, your connection is dropping the download;
   switching to a phone hotspot temporarily often fixes this.
4. Once you see `INFO: Application startup complete.`, the server is ready
   and running. Leave this terminal open — don't close it, don't type in it.
   This model download only happens once; after that it's cached and works
   offline.

---

## STEP 7 — Run the frontend

1. Open a **second, separate terminal** (leave the server one running).
2. Navigate to the frontend folder:
   ```
   cd Downloads\speech-app\frontend
   ```
3. Start a simple local web server:
   ```
   python -m http.server 5500
   ```
4. Open Chrome and go to:
   ```
   http://localhost:5500
   ```
5. Allow microphone access when prompted. You should see "Microphone ready.
   Click Start."

---

## STEP 8 — Test it

1. Click **Start Session**.
2. Speak for 30-60 seconds, mixing Urdu/Hindi/Punjabi/English if you can —
   that's what the assignment is actually testing.
3. Text should start appearing in the Transcript box after the first 8-second
   chunk finishes (there's a short delay, that's normal — local transcription
   is slower than a cloud API).
4. Click **End Session**. Wait a few seconds — the Summary box should fill in
   with an English summary from Gemini.
5. Watch the uvicorn terminal while you do this — errors, if any, print there.

If transcript/summary stay empty, check that terminal for red text and send
it to me exactly as printed.

---

## STEP 9 — Git setup and commit history

1. Confirm Git is installed:
   ```
   git --version
   ```
   Install from git-scm.com if missing.
2. From the project root (`speech-app`, not `backend`):
   ```
   git init
   ```
3. Create `.gitignore` in the project root with:
   ```
   venv/
   __pycache__/
   .env
   ```
   This keeps your real Gemini key and the huge venv folder out of the repo.
4. Commit in stages, not all at once:
   ```
   git add backend/requirements.txt backend/.env.example .gitignore
   git commit -m "Set up backend project structure"

   git add backend/server.py
   git commit -m "Add WebSocket server with local Whisper transcription and Gemini summarization"

   git add frontend/index.html
   git commit -m "Add frontend with mic capture and live transcript display"

   git add README.md
   git commit -m "Add README with architecture and setup instructions"
   ```
5. Push to GitHub: create a new empty repo on github.com (don't add a README
   there, you already have one), then:
   ```
   git remote add origin https://github.com/yourusername/your-repo-name.git
   git branch -M main
   git push -u origin main
   ```

---

## STEP 10 — Produce the required deliverables

1. **Sample output:** run one real multilingual session end to end, copy the
   transcript and summary text into the "Sample output" section at the
   bottom of `README.md`. Commit that change.
2. **Demo video (2-4 min):** screen-record (Win+G on Windows) showing: mic
   permission → Start Session → you talking with a language switch → End
   Session → transcript and summary appearing.
3. **Check GitHub online** that `.env` is NOT visible in your repo. If it is,
   run `git rm --cached backend/.env`, commit, and generate a new Gemini key
   to replace the exposed one.

---

## STEP 11 — Setting this up on a different device

Anyone (including you, on another machine) does this from a fresh clone:
```
git clone https://github.com/yourusername/your-repo-name.git
cd your-repo-name/backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```
Then edit `.env` with their own Gemini key, run
`uvicorn server:app --reload --port 8000`, and open `frontend/index.html`
the same way. The Whisper model re-downloads automatically on that machine
the first time — that's expected, it's not part of the Git repo.

---

## STEP 12 — Submit

Send Shah the GitHub repo link, confirm README, sample output, and demo
video are all in place, before Monday, 10 August.

---

## If something goes wrong

Tell me the exact step number and paste the exact error text — copy it
exactly, don't paraphrase.
