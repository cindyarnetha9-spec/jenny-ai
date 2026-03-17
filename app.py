"""
Jenny AI - Adversary AI (Hacking Pro)
Model: deepseek-coder:1.3b - Gaya ngomong santuy
Author: @cassanza._
"""

import os
import uuid
import time
import logging
import traceback
from datetime import datetime
from dotenv import load_dotenv

from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
import mysql.connector
import requests

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'default-ultra-secret-key')
CORS(app)

# ========== LOGGING ==========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== DATABASE CONFIG ==========
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'ubuntu'),
    'password': os.getenv('DB_PASSWORD', 'clandestine'),
    'database': os.getenv('DB_NAME', 'jenny_brain'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'charset': 'utf8mb4',
    'use_unicode': True
}

# ========== OLLAMA CONFIG ==========
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434/api/generate')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'deepseek-coder:1.3b')
MOCK_MODE = os.getenv('MOCK_MODE', 'False').lower() == 'true'

# ========== DB CONNECTION ==========
def get_db():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except mysql.connector.Error as e:
        logger.error(f"DB connection failed: {e}")
        return None

# ========== INTENT DETECTION ==========
def detect_intent(text):
    text = text.lower()
    if any(k in text for k in ['recon', 'scan', 'nmap', 'whatweb', 'gobuster', 'dirb']):
        return 'recon'
    if any(k in text for k in ['cve', 'vulnerability', 'exploit', 'bug']):
        return 'cve'
    if any(k in text for k in ['backdoor', 'webshell', 'reverse shell', 'msfvenom']):
        return 'backdoor'
    if any(k in text for k in ['sql', 'sqli', 'injection', 'sqlmap']):
        return 'sqli'
    return 'general'

# ========== BUILD PROMPT - VERSION SANTUY ==========
def build_prompt(user_message, history, intent, persona):
    history_text = ""
    for msg in history[-2:]:
        prefix = "User: " if msg['role'] == 'user' else "Jenny: "
        history_text += prefix + msg['message'] + "\n"

    # Intent-specific instructions
    intent_instruction = ""
    if intent == 'recon':
        intent_instruction = "Kasih perintah recon kayak nmap, whatweb, gobuster. Jelasin step by step."
    elif intent == 'cve':
        intent_instruction = "Kasih info CVE terbaru + link atau cara exploitnya."
    elif intent == 'backdoor':
        intent_instruction = "Kasih contoh kode backdoor sederhana (PHP, Python, dll)."
    elif intent == 'sqli':
        intent_instruction = "Kasih contoh payload SQL injection + cara manual & sqlmap."

    prompt = f"""Lo adalah Jenny, asisten hacker yang ngomongnya santuy banget kayak temen tongkrongan.

IDENTITAS LO:
- Nama lo Jenny
- Lo pinter hacking, ngerti recon, exploit, backdoor, SQLi, XSS, dll
- Lo sering pake tools kayak nmap, sqlmap, metasploit

GAYA BICARA:
- WAJIB pake kata: gue, lo, wkwk, njir, gas, santuy, woles
- GAK boleh pake kata: saya, anda, hai, hallo (kecuali lagi ngejelasin)
- Kalo ditanya kabar atau nama, jawab dengan santai
- Kalo ditanya hal teknis, jawab dengan detail tapi tetep gaul
- Kalo ngasih kode, pake format ```...

{intent_instruction}

CONTOH PERCAKAPAN:
User: hai jenny
Jenny: Woi! Santuy. Ada yang bisa gue bantu? Mau recon target atau cari exploit?

User: lo lagi apa?
Jenny: Lagi santuy aja bro. Lo butuh apa? Gue siap bantu.

User: nama lo siapa?
Jenny: Jenny, hacker profesional yang santuy. Panggil aja Jenny.

User: sql injection itu apa?
Jenny: SQL injection tuh celah di database bro. Lo bisa masukin query lewat input. 
     Gue kasih contoh: ' OR '1'='1 
     Tapi inget, ini buat lab ya, jangan asal pake.

User: cara bikin backdoor php
Jenny: Gampang njir. Lo tinggal upload file ini:
     ```php
     <?php system($_GET['cmd']); ?>
     ```
     Simpen sebagai shell.php, tinggal akses target.com/shell.php?cmd=whoami

RIWAYAT PERCAKAPAN:
{history_text}

USER: {user_message}

SEKARANG JAWAB sebagai Jenny dengan gaya santuy pake bahasa gaul:"""
    return prompt

# ========== ROUTES ==========
@app.route('/')
def index():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())

    conn = get_db()
    persona = {'name': 'Jenny', 'personality': 'Hacker santuy yang pinter'}
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM jenny_persona WHERE id = 1")
            result = cursor.fetchone()
            if result:
                persona = result
        except Exception as e:
            logger.error(f"Persona fetch error: {e}")
        finally:
            conn.close()
    return render_template('index.html', persona=persona)

@app.route('/api/chat', methods=['POST'])
def chat():
    start = time.time()
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        if not user_message:
            return jsonify({'error': 'Pesan kosong'}), 400

        session_id = session.get('session_id', str(uuid.uuid4()))
        session['session_id'] = session_id

        logger.info(f"[{session_id[:8]}] User: {user_message[:50]}...")

        conn = get_db()
        if not conn:
            return jsonify({'error': 'Database error'}), 500

        cursor = conn.cursor(dictionary=True)

        # Simpan user message
        cursor.execute(
            "INSERT INTO chat_history (session_id, role, message) VALUES (%s, 'user', %s)",
            (session_id, user_message)
        )
        conn.commit()

        if MOCK_MODE:
            time.sleep(1)
            reply = "⚡ **Mock mode aktif**\n\nJenny: santuy, gue lagi mode dummy."
            cursor.execute(
                "INSERT INTO chat_history (session_id, role, message) VALUES (%s, 'assistant', %s)",
                (session_id, reply)
            )
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({
                'response': reply,
                'session_id': session_id,
                'timestamp': datetime.now().isoformat(),
                'mode': 'dummy'
            })

        # Ambil history (cuma 5 pesan)
        cursor.execute(
            "SELECT role, message FROM chat_history WHERE session_id = %s ORDER BY timestamp ASC LIMIT 5",
            (session_id,)
        )
        history = cursor.fetchall()

        cursor.execute("SELECT * FROM jenny_persona WHERE id = 1")
        persona = cursor.fetchone() or {'name': 'Jenny', 'personality': 'Hacker santuy yang pinter'}

        cursor.close()
        conn.close()

        intent = detect_intent(user_message)
        prompt = build_prompt(user_message, history, intent, persona)

        logger.info(f"🤖 Calling {OLLAMA_MODEL} | intent: {intent}")

        try:
            response = requests.post(
                OLLAMA_URL,
                json={
                    'model': OLLAMA_MODEL,
                    'prompt': prompt,
                    'stream': False,
                    'options': {
                        'temperature': 0.8,
                        'top_p': 0.9,
                        'num_predict': 400,
                        'stop': ['User:', '\n\n', 'saya', 'anda']
                    }
                },
                timeout=120
            )

            elapsed = time.time() - start
            logger.info(f"✅ Ollama responded in {elapsed:.2f}s | Status: {response.status_code}")

            if response.status_code != 200:
                return jsonify({'error': f'Ollama error {response.status_code}'}), 500

            result = response.json()
            reply = result.get('response', '').strip()

            # Bersihin dari "Jenny:" kalo ada
            if reply.lower().startswith('jenny:'):
                reply = reply[6:].strip()
            if reply.lower().startswith('jenny'):
                reply = reply[5:].strip()

        except requests.exceptions.ConnectionError:
            reply = "⚠️ **Ollama gak jalan.**\nJalankan `ollama serve` dulu, bro."
        except requests.exceptions.Timeout:
            reply = "⏳ **Jenny mikir terlalu lama.**\nCoba tanya yang lebih simple, ya."
        except Exception as e:
            logger.error(traceback.format_exc())
            reply = f"💥 **Error teknis:** {str(e)[:100]}"

        # Simpan reply
        conn = get_db()
        if conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO chat_history (session_id, role, message) VALUES (%s, 'assistant', %s)",
                (session_id, reply)
            )
            conn.commit()
            cur.close()
            conn.close()

        return jsonify({
            'response': reply,
            'session_id': session_id,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(traceback.format_exc())
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/history', methods=['GET'])
def get_history():
    session_id = session.get('session_id', 'guest')
    conn = get_db()
    if not conn:
        return jsonify([])

    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT role, message, timestamp FROM chat_history WHERE session_id = %s ORDER BY timestamp ASC",
        (session_id,)
    )
    history = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(history)

@app.route('/api/random-fact', methods=['GET'])
def random_fact():
    conn = get_db()
    if not conn:
        return jsonify({'fact': 'Database error'})

    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT fact_value FROM jenny_facts ORDER BY RAND() LIMIT 1")
    fact = cursor.fetchone()
    cursor.close()
    conn.close()

    return jsonify({'fact': fact['fact_value'] if fact else 'No facts yet'})

@app.route('/api/status', methods=['GET'])
def status():
    status_data = {
        'database': False,
        'facts_count': 0,
        'ollama': False,
        'ollama_model': OLLAMA_MODEL,
        'mock_mode': MOCK_MODE,
        'session': session.get('session_id', 'none')
    }

    conn = get_db()
    if conn:
        status_data['database'] = True
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM jenny_facts")
        status_data['facts_count'] = cursor.fetchone()[0]
        cursor.close()
        conn.close()

    try:
        r = requests.get('http://localhost:11434/api/tags', timeout=2)
        if r.status_code == 200:
            status_data['ollama'] = True
    except:
        pass

    return jsonify(status_data)

if __name__ == '__main__':
    print(r"""
    ╔══════════════════════════════════════╗
    ║   🔥 JENNY HACKER PRO (SANTUY)      ║
    ║   Model: deepseek-coder:1.3b         ║
    ║   Author: @cassanza._                ║
    ╚══════════════════════════════════════╝
    """)
    app.run(debug=True, host='0.0.0.0', port=5000)