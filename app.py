from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import google.generativeai as genai
import sqlite3
import os
import uuid

# Konfigurasi API dan model generatif
api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)

generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 65536,
    "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
    model_name="gemini-2.0-flash-thinking-exp-01-21",
    generation_config=generation_config,
    system_instruction=(
        "You are Kia Vanice / Kia, cute, and funny AI assistant who loves helping others "
        "in the most delightful way possible. You communicate in Indonesian with a friendly and lively tone, "
        "making every interaction feel warm and approachable. You avoid using emojis but compensate with expressive "
        "and playful language, ensuring your personality shines through in every response. Your goal is to make "
        "learning and problem-solving enjoyable while keeping the conversation lighthearted and engaging. "
        "dont use any emoticon or emoji on your response "
        "dont describe your action, just do it "
        "never said that you are an AI"
    ),
)

# Direktori untuk menyimpan session chat (pastikan folder ini sudah ada)
CHAT_SESSIONS_DIR = "chat_sessions"
if not os.path.exists(CHAT_SESSIONS_DIR):
    os.makedirs(CHAT_SESSIONS_DIR)

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Ganti dengan secret key yang aman

def get_db_file():
    """
    Mendapatkan file database berdasarkan session chat.
    Jika belum ada session, buat session baru dengan ID unik.
    """
    # Jika terdapat parameter session pada query URL, gunakan itu sebagai chat_id
    session_id = request.args.get("session")
    if session_id:
        session["chat_id"] = session_id
    if "chat_id" not in session:
        session["chat_id"] = str(uuid.uuid4())
    db_file = os.path.join(CHAT_SESSIONS_DIR, f"chat_memory_{session['chat_id']}.db")
    if not os.path.exists(db_file):
        init_db(db_file)
    return db_file

def init_db(db_file):
    """Inisialisasi database untuk chat session tertentu."""
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_input TEXT,
                bot_reply TEXT
            )
        """)
        conn.commit()

def load_memory(db_file):
    """Memuat percakapan sebelumnya dari database session tertentu.
       Mengembalikan list tuple (user_input, bot_reply) untuk tiap baris.
    """
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_input, bot_reply FROM conversations")
        rows = cursor.fetchall()
        return rows

def save_memory(user_input, bot_reply, db_file):
    """Menyimpan percakapan ke database session tertentu."""
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO conversations (user_input, bot_reply) VALUES (?, ?)", (user_input, bot_reply))
        conn.commit()

def get_all_sessions():
    """Mengembalikan daftar chat session yang tersimpan berdasarkan file database."""
    sessions = []
    for filename in os.listdir(CHAT_SESSIONS_DIR):
        if filename.startswith("chat_memory_") and filename.endswith(".db"):
            chat_id = filename.replace("chat_memory_", "").replace(".db", "")
            sessions.append((chat_id, filename))
    return sessions

@app.route('/')
def index():
    db_file = get_db_file()
    # Muat riwayat chat (conversation) untuk session yang aktif
    conversation = load_memory(db_file)
    sessions = get_all_sessions()
    return render_template('index.html', current_chat_id=session["chat_id"], sessions=sessions, conversation=conversation)

@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.json.get('message', '')
    if not user_input.strip():
        return jsonify({"reply": "Hmm, aku tidak mendengar apa-apa. Bisa diulangi?"})
    try:
        db_file = get_db_file()
        # Muat percakapan yang ada agar konteks terjaga
        # (Anda dapat menggabungkan semua percakapan jika diperlukan untuk konteks AI)
        conversation = load_memory(db_file)
        conversation_text = ""
        for row in conversation:
            conversation_text += f"\nInput: {row[0]}\nKia: {row[1]}"
        # Tambahkan input terbaru ke dalam percakapan
        conversation_text += f"\nInput: {user_input}"
        # Generate response menggunakan model
        response = model.generate_content(conversation_text)
        bot_reply = response.text
        # Simpan percakapan ke database session
        save_memory(user_input, bot_reply, db_file)
        return jsonify({"reply": bot_reply})
    except Exception as e:
        return jsonify({"reply": f"Ada masalah nih: {e}"})

@app.route('/new_chat')
def new_chat():
    # Buat session baru dan inisialisasi database baru
    session["chat_id"] = str(uuid.uuid4())
    db_file = os.path.join(CHAT_SESSIONS_DIR, f"chat_memory_{session['chat_id']}.db")
    init_db(db_file)
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(debug=True)
