"""
Asistente de Estudio para Devs - Backend
-----------------------------------------
Servidor Flask que recibe mensajes del chat web y los envía
a la API de Groq para obtener respuestas.
"""

import os
import uuid
from flask import Flask, request, jsonify, render_template, Response, stream_with_context, session, abort
from groq import Groq
from dotenv import load_dotenv

import db

load_dotenv()

app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY", "cambia-esto-en-produccion")

# Inicializa las tablas en la base de datos
db.init_db()

# Cliente de Groq
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

SYSTEM_PROMPT = (
    "Eres un tutor de programación paciente y claro, especializado en ayudar "
    "a estudiantes y desarrolladores junior a entender conceptos técnicos "
    "(desarrollo web, Python, bases de datos, cloud/AWS, buenas prácticas). "
    "Explica con ejemplos simples, usa bloques de código cuando ayude a "
    "entender, y si el estudiante parece confundido, ofrece analogías. "
    "Responde siempre en español, de forma concisa pero completa."
)


def get_session_id():
    """Obtiene el session_id de la cookie de Flask, o crea uno nuevo."""
    session.permanent = True  # Mantiene la cookie activa al recargar la página
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    sid = session["session_id"]
    db.ensure_session(sid)
    return sid


@app.route("/")
def home():
    get_session_id()
    return render_template("index.html")


@app.route("/history", methods=["GET"])
def history():
    sid = get_session_id()
    return jsonify({"messages": db.get_history(sid)})


@app.route("/chat", methods=["POST"])
def chat():
    sid = get_session_id()
    data = request.get_json()
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"error": "Mensaje vacío"}), 400

    db.add_message(sid, "user", user_message)

    def generate():
        full_reply = ""
        try:
            chat_history = db.get_history(sid)
            messages = [{"role": "system", "content": SYSTEM_PROMPT}] + chat_history

            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                max_tokens=1024,
                messages=messages,
                stream=True,
            )

            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    full_reply += content
                    safe_content = content.replace("\n", "\\n")
                    yield f"data: {safe_content}\n\n"

            db.add_message(sid, "assistant", full_reply)
            yield "event: done\ndata: end\n\n"

        except Exception as e:
            yield f"event: error\ndata: {str(e)}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.route("/reset", methods=["POST"])
def reset():
    """Limpia el historial de la sesión activa."""
    sid = get_session_id()
    db.clear_history(sid)
    return jsonify({"status": "ok"})


@app.route("/admin/download-db", methods=["GET"])
def download_db():
    return jsonify({"info": "La base de datos está gestionada en Supabase."}), 200


if __name__ == "__main__":
    app.run(debug=True, port=5000, threaded=True)