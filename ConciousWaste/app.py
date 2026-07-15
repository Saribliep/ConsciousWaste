"""
Survey App — app.py
Saves answers to survey.db, handles audio upload,
and generates TTS via Mistral API in a background thread.
"""

import os
import uuid
import sqlite3
import threading
import base64
from datetime import datetime
from flask import Flask, request, render_template, jsonify, send_from_directory

# pip install mistralai
from mistralai.client import Mistral

app = Flask(__name__)

# ── Config ─────────────────────────────────────────────────────────────────
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
TTS_FOLDER    = os.path.join(os.path.dirname(__file__), 'static', 'tts')
DB_PATH       = os.path.join(os.path.dirname(__file__), 'survey.db')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TTS_FOLDER,    exist_ok=True)

MISTRAL_API_KEY = os.environ.get('MISTRAL_API_KEY', '')

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
                q11 TEXT, gender TEXT, audio_file TEXT, tts_file TEXT
            )
        """)
        existing = {row[1] for row in conn.execute("PRAGMA table_info(responses)")}
        for col in ['submitted_at','q1','q2','q3','q4','q5','q6','q7',
                    'q8','q9','q10','q11','gender','audio_file','tts_file']:
            if col not in existing:
                conn.execute(f"ALTER TABLE responses ADD COLUMN {col} TEXT")
        conn.commit()


init_db()


# ── TTS worker (runs in background thread) ──────────────────────────────────
def run_tts(job_id: str, audio_path: str, gender: str = ''):
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
        # The text to synthesise in the user's cloned voice:
        tts_text = (
            "Wat een verbetering wordt het als deze muur hier weg is. Ik wil morgen de keuze maken wat ik doe met de tegels in de keuken en het scheiden van mijn bouwafval..." 
            "Ik neig naar mijn tegels niet hergebruiken maar wel mijn afval scheiden..." 
            "Ik kan prima wat extra geld stoppen in het mogelijk maken dat ik mijn afval scheid maar vind het extra tijd wat het hergebruiken van tegels met zich mee brengt teveel."
        )

        response = client.audio.speech.complete(
            model="voxtral-mini-tts-2603",   # official model name from docs
            input=tts_text,
            voice_id=voice_id,               # use the voice we just created
            response_format="mp3",
        )

        # ── Step 4: decode and save the output audio ─────────────────────────
        # response.audio_data is a base64-encoded string
        out_filename = f"{job_id}.mp3"
        out_path     = os.path.join(TTS_FOLDER, out_filename)
        with open(out_path, 'wb') as f:
            f.write(base64.b64decode(response.audio_data))

        tts_jobs[job_id] = {
            'status':    'done',
            'audio_url': f'/static/tts/{out_filename}'
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

    # Save to DB
    with get_db() as conn:
        conn.execute(
            f"""INSERT INTO responses
                (submitted_at, {', '.join(fields)}, gender, audio_file)
                VALUES (?, {', '.join(['?']*len(fields))}, ?, ?)""",
            [datetime.utcnow().isoformat()] + [vals[f] for f in fields] + [gender, audio_filename]
        )
        conn.commit()

    # Start TTS job in background
    job_id = str(uuid.uuid4())
    tts_jobs[job_id] = {'status': 'pending'}

    if audio_path and MISTRAL_API_KEY:
        thread = threading.Thread(target=run_tts, args=(job_id, audio_path, gender), daemon=True)
        thread.start()
    else:
        # No API key or no audio — mark as error so frontend can still proceed
        tts_jobs[job_id] = {'status': 'error', 'message': 'Geen API key of audio beschikbaar'}

    return jsonify({'status': 'ok', 'job_id': job_id}), 200


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
