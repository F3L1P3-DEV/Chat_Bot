"""
Asistente de Estudio para Devs - Backend
-----------------------------------------
Servidor Flask que recibe mensajes del chat web y los envía
a la API de Groq (gratuita, sin tarjeta de crédito) para obtener
una respuesta usando un modelo de código abierto (Llama 3.3).
"""

import os
import uuid
from flask import Flask, request, jsonify, render_template, Response, stream_with_context, session, send_file, abort
from groq import Groq
from dotenv import load_dotenv

import db

load_dotenv()  # Carga variables desde el archivo .env

app = Flask(__name__)

# Necesaria para firmar la cookie de sesión (identifica a cada visitante).
# En producción, ponla en el .env como SECRET_KEY y NO uses el valor por defecto.
app.secret_key = os.environ.get("SECRET_KEY", "cambia-esto-en-produccion")

db.init_db()

# Cliente de Groq (lee la API key desde la variable de entorno GROQ_API_KEY)
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Prompt de sistema: define la personalidad y el enfoque del asistente
SYSTEM_PROMPT = (
    "Eres un tutor de programación paciente y claro, especializado en ayudar "
    "a estudiantes y desarrolladores junior a entender conceptos técnicos "
    "(desarrollo web, Python, bases de datos, cloud/AWS, buenas prácticas). "
    "Explica con ejemplos simples, usa bloques de código cuando ayude a "
    "entender, y si el estudiante parece confundido, ofrece analogías. "
    "Responde siempre en español, de forma concisa pero completa."
)

def get_session_id():
    """Obtiene el session_id de la cookie de Flask, o crea uno nuevo
    si es la primera visita. Así cada visitante tiene su propio historial."""
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    sid = session["session_id"]
    db.ensure_session(sid)
    return sid


@app.route("/")
def home():
    """Sirve la página principal del chat."""
    get_session_id()  # asegura que exista la cookie desde la primera carga
    return render_template("index.html")


@app.route("/history", methods=["GET"])
def history():
    """Devuelve el historial guardado de esta sesión (para repintar el
    chat si el usuario recarga la página)."""
    sid = get_session_id()
    return jsonify({"messages": db.get_history(sid)})


@app.route("/chat", methods=["POST"])
def chat():
    """Recibe un mensaje del usuario y transmite (streaming) la respuesta de Groq."""
    sid = get_session_id()
    data = request.get_json()
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"error": "Mensaje vacío"}), 400

    # Guarda el mensaje del usuario en la base de datos
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
                    # Cada línea "data: ..." es un evento SSE. \n dentro del
                    # texto se escapan para no romper el formato del protocolo.
                    safe_content = content.replace("\n", "\\n")
                    yield f"data: {safe_content}\n\n"

            # Guarda la respuesta completa en la base de datos una vez terminó
            db.add_message(sid, "assistant", full_reply)
            yield "event: done\ndata: end\n\n"

        except Exception as e:
            yield f"event: error\ndata: {str(e)}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # evita que un proxy (ej. nginx) bufferee el stream
        },
    )


@app.route("/reset", methods=["POST"])
def reset():
    """Limpia el historial de conversación (botón 'Nueva conversación')."""
    sid = get_session_id()
    db.clear_history(sid)
    return jsonify({"status": "ok"})


@app.route("/admin/download-db", methods=["GET"])
def download_db():
    """
    Descarga el archivo completo de la base de datos (chat_history.db).
    Protegida con una clave secreta que va en la URL: ?key=TU_CLAVE

    Configura ADMIN_KEY en las variables de entorno (local: .env,
    en Render: dashboard > Environment). Si no la configuras, esta
    ruta queda deshabilitada por seguridad.
    """
    admin_key = os.environ.get("ADMIN_KEY")

    if not admin_key:
        abort(404)  # ruta "no existe" si no configuraste una clave

    provided_key = request.args.get("key", "")
    if provided_key != admin_key:
        abort(403)  # clave incorrecta o ausente

    return send_file(db.DB_PATH, as_attachment=True, download_name="chat_history.db")


if __name__ == "__main__":
    app.run(debug=True, port=5000, threaded=True)
