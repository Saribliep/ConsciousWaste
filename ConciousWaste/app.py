"""
Survey App — app.py
Saves answers to survey.db, handles audio upload,
and generates TTS via Mistral API in a background thread.
"""

import os
import sys
import uuid
import sqlite3
import threading
import base64
from datetime import datetime
from flask import Flask, request, render_template, jsonify, send_from_directory

# pip install mistralai
from mistralai.client import Mistral

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'utils'))
from tts_text import create_tss_text

app = Flask(__name__)

# ── Config ─────────────────────────────────────────────────────────────────
# DATA_DIR holds everything that must survive redeploys/restarts (recordings,
# generated audio, the DB). Defaults to the project folder for local dev; in
# production, point it at a mounted persistent volume.
DATA_DIR      = os.environ.get('DATA_DIR', os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(DATA_DIR, 'uploads')
TTS_FOLDER    = os.path.join(DATA_DIR, 'tts')
DB_PATH       = os.path.join(DATA_DIR, 'survey.db')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TTS_FOLDER,    exist_ok=True)

MISTRAL_API_KEY = os.environ.get('MISTRAL_API_KEY', '')
MOCK_TTS        = os.environ.get('MOCK_TTS', '0') == '1'

# In-memory job store  {job_id: {'status': 'pending'|'done'|'error', 'audio_url': ...}}
tts_jobs = {}


# ── Database ────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS responses (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                submitted_at TEXT,
                q1 TEXT, q2 TEXT, q3 TEXT, q4 TEXT, q5 TEXT,
                q6 TEXT, q7 TEXT, q8 TEXT, q9 TEXT, q10 TEXT,
                q11 TEXT, gender TEXT, audio_file TEXT, tts_file TEXT, tts_text TEXT
            )
        """)
        existing = {row[1] for row in conn.execute("PRAGMA table_info(responses)")}
        for col in ['submitted_at','q1','q2','q3','q4','q5','q6','q7',
                    'q8','q9','q10','q11','gender','audio_file','tts_file','tts_text']:
            if col not in existing:
                conn.execute(f"ALTER TABLE responses ADD COLUMN {col} TEXT")
        conn.commit()


init_db()


# ── TTS worker (runs in background thread) ──────────────────────────────────
def run_tts(job_id: str, audio_path: str, vals: dict, response_id: int, gender: str = ''):
    """
    Correct Mistral TTS flow (according to docs.mistral.ai/capabilities/audio/):

    Step 1: base64-encode the user's audio and create a temporary voice profile
            via client.audio.voices.create() → returns a voice_id
    Step 2: call client.audio.speech.complete() with that voice_id to synthesise
            new text in the user's cloned voice
    Step 3: decode the returned base64 audio and save it as an mp3

    The parameter that caused the original error was passing raw bytes to
    voice_sample=. The API expects a base64-encoded *string*, not bytes.
    """
    # The text that would normally be synthesised in the user's cloned voice.
    # Defined up front so mock mode can return it without touching the API.
    tts_text = create_tss_text(vals)

    if MOCK_TTS:
        # Dry-run: skip both Mistral calls entirely and just hand back the
        # text that would have been sent for voice cloning / TTS.
        naam = vals.get('q1', '')
        answers_str = ', '.join(f"{k}={v}" for k, v in vals.items())
        print(f"[MOCK_TTS] job {job_id} — naam: {naam}")
        print(f"[MOCK_TTS] job {job_id} — answers: {answers_str}")
        print(f"[MOCK_TTS] job {job_id} — text that would be synthesised:\n{tts_text}")
        tts_jobs[job_id] = {
            'status':    'done',
            'audio_url': None,
            'text':      tts_text,
            'naam':      naam,
            'answers':   vals,
        }
        return

    client = Mistral(api_key=MISTRAL_API_KEY)
    voice_id = None

    try:
        # ── Step 1: base64-encode the recorded audio ─────────────────────────
        # The API requires a base64 string, NOT raw bytes — that was the bug.
        with open(audio_path, 'rb') as f:
            audio_b64 = base64.b64encode(f.read()).decode('utf-8')

        # Derive a filename with the right extension for format detection
        audio_filename = os.path.basename(audio_path)  # e.g. recording_....webm

        # ── Step 2: create a temporary voice profile ─────────────────────────
        _gender_map = {'V': 'female', 'M': 'male', 'N': 'neutral'}
        voice_kwargs = dict(
            name=f"survey-voice-{job_id[:8]}",
            sample_audio=audio_b64,
            sample_filename=audio_filename,
            languages=["nl"],
        )
        if gender in _gender_map:
            voice_kwargs['gender'] = _gender_map[gender]

        voice = client.audio.voices.create(**voice_kwargs)

        print(f"Creating voice profile for job {job_id} using {audio_filename}")
        voice_id = voice.id

        # ── Call Mistral TTS with voice cloning ─────────────────────────────
        response = client.audio.speech.complete(
            model="voxtral-mini-tts-2603",   # official model name from docs
            input=tts_text,
            voice_id=voice_id,               # use the voice we just created
            response_format="mp3",
        )

        # ── Step 4: decode and save the output audio ─────────────────────────
        # response.audio_data is a base64-encoded string
        if getattr(response, 'audio_data', None):
            print(f"TTS job {job_id}: audio_data received from Mistral API ({len(response.audio_data)} b64 chars)")
        else:
            print(f"TTS job {job_id}: no audio_data in Mistral API response — {response}")

        out_filename = f"{job_id}.mp3"
        out_path     = os.path.join(TTS_FOLDER, out_filename)
        with open(out_path, 'wb') as f:
            f.write(base64.b64decode(response.audio_data))

        # Persist the mp3 filename against the survey response it belongs to
        with get_db() as conn:
            conn.execute(
                "UPDATE responses SET tts_file = ? WHERE id = ?",
                (out_filename, response_id)
            )
            conn.commit()

        tts_jobs[job_id] = {
            'status':    'done',
            'audio_url': f'/tts_audio/{out_filename}'
        }

    # except Exception as e:
    #     print(f"TTS error for job {job_id}: {e}")
    #     tts_jobs[job_id] = {'status': 'error', 'message': str(e)}

    except Exception as e:
        import traceback
        print(f"TTS error for job {job_id}:")
        traceback.print_exc()          # ← prints the full error with line numbers
        tts_jobs[job_id] = {'status': 'error', 'message': str(e)}

    finally:
        # ── Clean up: delete the temporary voice profile ──────────────────────
        # This avoids cluttering your Mistral account with one voice per user.
        if voice_id:
            try:
                client.audio.voices.delete(voice_id)
            except Exception:
                pass

# ── Routes ──────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/submit', methods=['POST'])
def submit():
    # Collect all question answers
    fields = ['q1','q2','q3','q4','q5','q6','q7','q8','q9','q10','q11']
    vals   = {f: request.form.get(f, '').strip() for f in fields}
    gender = request.form.get('gender', '').strip()

    # Save user audio
    audio_filename = None
    audio_path     = None
    audio_file     = request.files.get('audio')
    if audio_file and audio_file.filename:
        timestamp      = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
        audio_filename = f'recording_{timestamp}.webm'
        audio_path     = os.path.join(UPLOAD_FOLDER, audio_filename)
        audio_file.save(audio_path)

    # Build the personalized monologue now — it only depends on the answers,
    # not on the audio/API call, so it can be saved alongside the response.
    tts_text = create_tss_text(vals)

    # Save to DB
    with get_db() as conn:
        cur = conn.execute(
            f"""INSERT INTO responses
                (submitted_at, {', '.join(fields)}, gender, audio_file, tts_text)
                VALUES (?, {', '.join(['?']*len(fields))}, ?, ?, ?)""",
            [datetime.utcnow().isoformat()] + [vals[f] for f in fields] + [gender, audio_filename, tts_text]
        )
        conn.commit()
        response_id = cur.lastrowid

    # Start TTS job in background
    job_id = str(uuid.uuid4())
    tts_jobs[job_id] = {'status': 'pending'}

    if audio_path and (MISTRAL_API_KEY or MOCK_TTS):
        thread = threading.Thread(target=run_tts, args=(job_id, audio_path, vals, response_id, gender), daemon=True)
        thread.start()
    else:
        # No API key or no audio — mark as error so frontend can still proceed
        tts_jobs[job_id] = {'status': 'error', 'message': 'Geen API key of audio beschikbaar'}

    return jsonify({'status': 'ok', 'job_id': job_id}), 200


@app.route('/tts_audio/<filename>')
def tts_audio(filename):
    return send_from_directory(TTS_FOLDER, filename)


@app.route('/tts_status/<job_id>')
def tts_status(job_id):
    job = tts_jobs.get(job_id, {'status': 'error', 'message': 'Job niet gevonden'})
    return jsonify(job)


@app.route('/responses')
def responses():
    with get_db() as conn:
        rows = conn.execute('SELECT * FROM responses ORDER BY id DESC').fetchall()
    return jsonify([dict(row) for row in rows])


if __name__ == '__main__':
    app.run(debug=True)
