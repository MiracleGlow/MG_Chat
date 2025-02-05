from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
import sqlite3
import os

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
        "learning and problem-solving enjoyable while keeping the conversation lighthearted and engaging."
        "dont use any emoticon or emoji on your response "
        "dont describe your action, just do it "
        "never said that you are an AI"
    ),
)

DB_FILE = "chat_memory.db"

def init_db():
    """Inisialisasi database."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_input TEXT,
                bot_reply TEXT
            )
        """)
        conn.commit()

def load_memory():
    """Memuat percakapan sebelumnya dari database."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_input, bot_reply FROM conversations")
        rows = cursor.fetchall()
        return "\n".join([f"Input: {row[0]}\nKia: {row[1]}" for row in rows])

def save_memory(user_input, bot_reply):
    """Menyimpan percakapan ke database."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO conversations (user_input, bot_reply) VALUES (?, ?)", (user_input, bot_reply))
        conn.commit()

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.json.get('message', '')
    if not user_input.strip():
        return jsonify({"reply": "Hmm, aku tidak mendengar apa-apa. Bisa diulangi?"})

    try:
        conversation = load_memory()

        # Tambahkan input terbaru ke dalam percakapan
        conversation += f"\nInput: {user_input}"

        # Generate response
        response = model.generate_content(conversation)
        bot_reply = response.text

        # Simpan percakapan ke database
        save_memory(user_input, bot_reply)

        return jsonify({"reply": bot_reply})
    except Exception as e:
        return jsonify({"reply": f"Ada masalah nih: {e}"})

if __name__ == "__main__":
    init_db()  # Pastikan database terinisialisasi
    app.run(debug=True)
