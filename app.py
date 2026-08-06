"""
Asistente de Estudio para Devs - Backend
-----------------------------------------
Servidor Flask que recibe mensajes del chat web y los envía
a la API de Groq (gratuita, sin tarjeta de crédito) para obtener
una respuesta usando un modelo de código abierto (Llama 3.3).
"""

import os
from flask import Flask, request, jsonify, render_template
from groq import Groq
from dotenv import load_dotenv

load_dotenv()  # Carga variables desde el archivo .env

app = Flask(__name__)

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

# Guardamos el historial de conversación en memoria (simple, por sesión de servidor)
conversation_history = []


@app.route("/")
def home():
    """Sirve la página principal del chat."""
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    """Recibe un mensaje del usuario y devuelve la respuesta de Claude."""
    data = request.get_json()
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"error": "Mensaje vacío"}), 400

    # Agrega el mensaje del usuario al historial
    conversation_history.append({"role": "user", "content": user_message})

    try:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + conversation_history

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=1024,
            messages=messages,
        )
        assistant_reply = response.choices[0].message.content

        # Agrega la respuesta al historial para mantener el contexto
        conversation_history.append({"role": "assistant", "content": assistant_reply})

        return jsonify({"reply": assistant_reply})

    except Exception as e:
        return jsonify({"error": f"Error al contactar la API: {str(e)}"}), 500


@app.route("/reset", methods=["POST"])
def reset():
    """Limpia el historial de conversación (botón 'Nueva conversación')."""
    conversation_history.clear()
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
