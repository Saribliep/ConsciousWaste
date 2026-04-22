"""
Survey App — app.py
Saves answers to survey.db (SQLite) and audio files to uploads/
"""
 
import os
import sqlite3
from datetime import datetime
from flask import Flask, request, render_template, jsonify
 
app = Flask(__name__)
 
# ── Config ─────────────────────────────────────────────────────────────────
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
DB_PATH       = os.path.join(os.path.dirname(__file__), 'survey.db')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
 
 
# ── Database setup ──────────────────────────────────────────────────────────
def get_db():
    """Open a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
 
 
def init_db():
    """Create the responses table if it doesn't exist, and add any missing columns."""
    with get_db() as conn:
        # Create table with all columns (safe if already exists)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS responses (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                submitted_at TEXT,
                q1           TEXT,
                q2           TEXT,
                q3           TEXT,
                audio_file   TEXT
            )
        """)
 
        # Migrate: add any columns that might be missing from an older table
        existing = {row[1] for row in conn.execute("PRAGMA table_info(responses)")}
        migrations = {
            'submitted_at': 'TEXT',
            'q1':           'TEXT',
            'q2':           'TEXT',
            'q3':           'TEXT',
            'audio_file':   'TEXT',
        }
        for col, col_type in migrations.items():
            if col not in existing:
                conn.execute(f"ALTER TABLE responses ADD COLUMN {col} {col_type}")
 
        conn.commit()
 
# ── Routes ──────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')
 
 
@app.route('/submit', methods=['POST'])
def submit():
    q1 = request.form.get('q1', '').strip()
    q2 = request.form.get('q2', '').strip()
    q3 = request.form.get('q3', '').strip()
 
    # Save audio file if present
    audio_filename = None
    audio_file = request.files.get('audio')
    if audio_file and audio_file.filename:
        timestamp      = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
        audio_filename = f'recording_{timestamp}.webm'
        audio_file.save(os.path.join(UPLOAD_FOLDER, audio_filename))
 
    # Store in database
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO responses (submitted_at, q1, q2, q3, audio_file)
            VALUES (?, ?, ?, ?, ?)
            """,
            (datetime.utcnow().isoformat(), q1, q2, q3, audio_filename)
        )
        conn.commit()
 
    return jsonify({'status': 'ok'}), 200
 
 
# Optional: simple admin view of all responses
@app.route('/responses')
def responses():
    with get_db() as conn:
        rows = conn.execute(
            'SELECT * FROM responses ORDER BY id DESC'
        ).fetchall()
    return jsonify([dict(row) for row in rows])
 
 
# ── Run ─────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True)