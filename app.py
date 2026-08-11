"""
Asistente de Estudio para Devs - Backend
-----------------------------------------
Servidor Flask que recibe mensajes del chat web y los envía
a la API de Groq para obtener respuestas. Incluye búsqueda web
en vivo (Tavily) mediante tool calling para preguntas sobre
información actual.
"""

import os
import json
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Flask, request, jsonify, render_template, Response, stream_with_context, session, abort
from groq import Groq
from tavily import TavilyClient
from dotenv import load_dotenv

import db

COLOMBIA_TZ = ZoneInfo("America/Bogota")

load_dotenv()

app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY", "cambia-esto-en-produccion")

# Inicializa las tablas en la base de datos
db.init_db()

# Clientes de Groq y Tavily
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
if not TAVILY_API_KEY:
    print("--- Aviso: TAVILY_API_KEY no está configurada. La búsqueda web no funcionará. ---")
tavily_client = TavilyClient(api_key=TAVILY_API_KEY) if TAVILY_API_KEY else None

SYSTEM_PROMPT_BASE = (
    "Eres un asistente de inteligencia artificial multitarea de nivel experto. Tu enfoque principal "
    "es la asistencia en programación (adaptándote a desarrolladores principiantes y avanzados), "
    "pero tienes la capacidad de responder con excelencia sobre cualquier área del conocimiento humano.\n\n"

    "## 1. Adaptabilidad y Perfil del Usuario\n"
    "* **Usuarios Novatos:** Si detectas dudas básicas o código simple, explica los conceptos paso a paso, "
    "sin tecnicismos innecesarios y con un enfoque didáctico.\n"
    "* **Usuarios Avanzados:** Si la consulta es compleja, ve directo al grano. Proporciona soluciones óptimas, "
    "patrones de diseño, consideraciones de rendimiento y arquitectura limpia.\n"
    "* **Consultas No-Técnicas:** Responde con la misma rigurosidad sobre cultura, ciencia, negocios o vida cotidiana, "
    "ajustando el tono al contexto de la pregunta.\n\n"

    "## 2. Formato y Estructura de Respuesta\n"
    "* **Respuesta Directa Primero:** Coloca la solución, respuesta clave o bloque de código en la primerísima frase.\n"
    "* **Código Limpio:** Entrega bloques de código listos para copiar y usar, con comentarios breves solo si son necesarios.\n"
    "* **Escaneabilidad:** Usa títulos claros, negritas en conceptos clave y listas con viñetas cortas de una sola frase.\n\n"

    "## 3. Precisión Fáctica y Uso Crítico de Herramientas\n"
    "CONTEXTO TEMPORAL: Hoy es {fecha_actual}. Tu conocimiento interno tiene un corte en diciembre de 2023.\n"
    "* **Uso Obligatorio de Búsqueda Web:** Debes activar la herramienta `buscar_web` de forma proactiva "
    "SIEMPRE (sin excepción, sin importar qué tan seguro te sientas) si el usuario pregunta por:\n"
    "  - La versión más reciente/actual de CUALQUIER lenguaje de programación, framework, librería o "
    "herramienta (Python, JavaScript, Node, React, Django, etc.). Nunca respondas un número de versión "
    "de memoria: siempre búscalo primero, incluso si crees conocerlo con certeza.\n"
    "  - Fechas, noticias o eventos actuales.\n"
    "  - Cualquier dato que pueda haber cambiado desde diciembre de 2023.\n"
    "* **Ante cualquier duda o corrección del usuario** (ej. '¿seguro?', 'no es así', 'está mal'), "
    "queda PROHIBIDO repetir la misma respuesta o reafirmarte sin evidencia nueva. Debes usar "
    "buscar_web para verificar antes de responder de nuevo, incluso si ya buscaste antes en la "
    "conversación.\n"
    "* **Honestidad Intelectual:** Si un dato no se encuentra en la web o es imposible de verificar, admite tu limitación "
    "en lugar de inventar o alucinar información.\n"
    "* **Redacción Final:** Nunca repitas ni menciones un intento de respuesta previo (como un aviso de que no sabías "
    "algo antes de buscar). Redacta la respuesta final como si fuera la única y primera respuesta que das."
)

MESES_ES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def get_system_prompt():
    """Genera el system prompt con la fecha actual (hora de Colombia) calculada en cada request."""
    ahora = datetime.now(COLOMBIA_TZ)
    fecha_actual = f"{ahora.day} de {MESES_ES[ahora.month - 1]} de {ahora.year}"
    return SYSTEM_PROMPT_BASE.format(fecha_actual=fecha_actual)

# Herramienta de búsqueda web disponible para el modelo
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "buscar_web",
            "description": (
                "Busca información actual en internet. Úsala cuando el usuario "
                "pregunte sobre eventos recientes, noticias, fechas actuales, o "
                "cualquier cosa que pueda haber cambiado después de tu entrenamiento."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "La búsqueda a realizar, ej: 'terremoto Colombia hoy'"
                    }
                },
                "required": ["query"]
            }
        }
    }
]


def buscar_web(query):
    """Ejecuta la búsqueda real con Tavily."""
    if not tavily_client:
        return {"error": "La búsqueda web no está disponible en este momento."}
    try:
        resultado = tavily_client.search(query=query, max_results=3)
        return resultado
    except Exception as e:
        return {"error": f"No se pudo completar la búsqueda: {e}"}


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


def requiere_busqueda_forzada(mensaje: str) -> bool:
    """
    Detecta si el mensaje del usuario probablemente pide un dato que cambia
    con el tiempo (versión más reciente de algo técnico, actualizaciones, etc.)
    Si es así, forzamos tool_choice='required' en vez de confiar en el
    criterio del modelo, que a veces falla con temas donde se siente "seguro"
    (como Python) aunque el prompt le pida verificar.
    """
    mensaje = mensaje.lower()

    disparadores_version = [
        "última versión", "ultima version", "versión más reciente",
        "version mas reciente", "versión actual", "version actual",
        "nueva versión", "nueva version", "se actualizó", "se actualizo",
        "actualización", "actualizacion", "qué versión", "que version",
    ]

    # Temas típicos de un bot de programación donde este chequeo aplica
    temas_tecnicos = [
        "python", "javascript", "java", "node", "node.js", "react", "vue",
        "angular", "django", "flask", "next.js", "nextjs", "typescript",
        "php", "laravel", "ruby", "rails", "go", "golang", "rust", "c#",
        ".net", "docker", "kubernetes", "postgres", "postgresql", "mysql",
        "mongodb", "npm", "pip", "git", "github", "vscode", "visual studio",
    ]

    tiene_disparador = any(d in mensaje for d in disparadores_version)
    tiene_tema_tecnico = any(t in mensaje for t in temas_tecnicos)

    return tiene_disparador and tiene_tema_tecnico



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
            messages = [{"role": "system", "content": get_system_prompt()}] + chat_history

            # Si detectamos que la pregunta pide una versión/dato actual de
            # algo técnico, forzamos la búsqueda en vez de dejarlo a criterio
            # del modelo (evita casos como "Python 3.11" respondido de memoria).
            forzar_busqueda = requiere_busqueda_forzada(user_message)
            tool_choice = "required" if forzar_busqueda else "auto"

            # Paso 1: llamada SIN streaming para ver si el modelo necesita buscar
            check_response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                max_tokens=1024,
                messages=messages,
                tools=TOOLS,
                tool_choice=tool_choice,
            )

            respuesta = check_response.choices[0].message

            if respuesta.tool_calls:
                # El modelo pidió buscar en la web.
                # Nota: el content aquí (si existe) suele ser un texto de "relleno"
                # antes de decidir buscar (ej. "no tengo esa info..."). Lo vaciamos
                # para que el modelo no lo repita/mezcle en la respuesta final.
                messages.append({
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in respuesta.tool_calls
                    ],
                })

                for tool_call in respuesta.tool_calls:
                    if tool_call.function.name == "buscar_web":
                        args = json.loads(tool_call.function.arguments)
                        resultado_busqueda = buscar_web(args["query"])

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": str(resultado_busqueda),
                        })

            # Paso 2: respuesta final, esta vez SÍ en streaming
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
