from flask import Flask, render_template, request, jsonify
import sqlite3
import requests

app = Flask(__name__)

# Initialize the database
def init_db():
    conn = sqlite3.connect('survey.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            q1 TEXT,
            q2 TEXT,
            audio BLOB
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    q1 = request.form['q1']
    q2 = request.form['q2']
    audio = request.files['audio'].read() if 'audio' in request.files else None

    conn = sqlite3.connect('survey.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO responses (q1, q2, audio) VALUES (?, ?, ?)
    ''', (q1, q2, audio))
    conn.commit()
    conn.close()

    # Call Mistral AI API for audio transformation
    if audio:
        mistral_api_url = 'https://api.mistral.ai/transform'  # Replace with the actual API endpoint
        headers = {
            'Authorization': 'Bearer YOUR_MISTRAL_API_KEY',  # Replace with your actual API key
            'Content-Type': 'audio/wav'
        }
        response = requests.post(mistral_api_url, headers=headers, data=audio)
        if response.status_code == 200:
            transformed_audio = response.content
            # Save or process the transformed audio as needed
        else:
            print('Error transforming audio:', response.status_code, response.text)

    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(debug=True)
