# ConciousWaste — CLAUDE.md

## Project
Experimental performance art installation by Laura den Boer and Sarah Parinussa.
Artist in Residence at Wapenveld, April 2026.
Goal: raise awareness around construction waste (bouwafval) through an interactive voice-cloning survey.

## What it does
Participants fill out a 14-page Dutch-language survey about construction waste decisions (tiles, walls, sorting waste).
At the end, they record their own voice reading a Dutch passage.
The app clones their voice using Mistral's Voxtral API and plays back a pre-written Dutch monologue in their own voice.

## Tech stack
- **Backend**: Python 3, Flask
- **Database**: SQLite (`survey.db`) — stores survey responses + filenames
- **AI/Audio**: Mistral AI SDK (`mistralai`) — `voxtral-mini-tts-2603` model for voice cloning TTS
- **Frontend**: Vanilla HTML/CSS/JS, Jinja2 templates, no framework
- **Audio capture**: Browser `MediaRecorder` API → `.webm` uploads
- **TTS output**: Base64-decoded MP3 files served from `DATA_DIR/tts/` via the `/tts_audio/<filename>` route

## Project structure
Note: the app used to live in a `ConciousWaste/` subfolder of this repo; it was
flattened to the repo root so hosting platforms (Railway) don't need a
"root directory" override to find `app.py`/`Procfile`/`requirements.txt`.
```
app.py                  # Flask app — routes, DB, TTS background thread
Procfile                # Production start command (gunicorn, single worker)
templates/index.html    # Single-page survey (14 pages, Dutch)
static/css/styles.css
static/js/script.js
static/audio/           # Pre-recorded intro fragment
uploads/                # Raw user audio recordings (.webm) — under DATA_DIR
tts/                    # Generated TTS output (per job_id UUID) — under DATA_DIR
src/utils/              # Utility scripts (speech_generation, voice, tts_text)
survey.db               # SQLite database — under DATA_DIR
requirements.txt        # Flask, requests, gunicorn, mistralai
```

## Environment setup
```bash
conda activate mistralai
export MISTRAL_API_KEY="yourkey"
cd /Users/sarahparinussa/code/BouwafvalBeukenblad/Voxtral
python app.py
```

`DATA_DIR` (env var) controls where `survey.db`, `uploads/`, and `tts/` live —
defaults to the project folder locally; in production it should point at a
mounted persistent volume so data survives restarts/redeploys.

## Key flows
1. User completes survey → POST `/submit` → saves to DB, saves `.webm` audio, starts background TTS thread
2. Background thread: base64-encodes audio → `client.audio.voices.create()` → `client.audio.speech.complete()` → saves MP3 → deletes temp voice profile
3. Frontend polls `/tts_status/<job_id>` until `done`, then plays the MP3

## Known details
- `MISTRAL_API_KEY` must be set in environment — no fallback
- Voice profiles are created and immediately deleted after TTS generation (cleanup in `finally` block)
- `tts_jobs` is in-memory only — restarting the server loses pending job state
- Survey has 11 question fields (q1–q11) + audio_file + tts_file in DB
- Dutch language only (`languages=["nl"]`)
