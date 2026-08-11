import os
from datetime import datetime
from groq import Groq
from tavily import TavilyClient

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
tavily_client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))

# Definimos la herramienta que el modelo puede usar
tools = [
    {
        "type": "function",
        "function": {
            "name": "buscar_web",
            "description": "Busca información actual en internet. Úsala cuando el usuario pregunte sobre eventos recientes, noticias, fechas actuales, o cualquier cosa que pueda haber cambiado después de tu entrenamiento.",
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
    """Ejecuta la búsqueda real con Tavily"""
    resultado = tavily_client.search(query=query, max_results=3)
    return resultado

def responder(conversation_history):
    fecha_actual = datetime.now().strftime("%d de %B de %Y")
    
    system_prompt_dinamico = f"""{SYSTEM_PROMPT}

Hoy es {fecha_actual}. Si necesitas info actual o reciente, usa la herramienta buscar_web."""

    messages = [{"role": "system", "content": system_prompt_dinamico}] + conversation_history

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=1024,
            messages=messages,
            tools=tools,
            tool_choice="auto"  # el modelo decide si necesita buscar o no
        )

        respuesta = response.choices[0].message

        # Si el modelo pidió usar la herramienta
        if respuesta.tool_calls:
            messages.append(respuesta)

            for tool_call in respuesta.tool_calls:
                if tool_call.function.name == "buscar_web":
                    import json
                    args = json.loads(tool_call.function.arguments)
                    resultado_busqueda = buscar_web(args["query"])

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(resultado_busqueda)
                    })

            # Segunda llamada: ahora el modelo redacta la respuesta final con los datos reales
            segunda_respuesta = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                max_tokens=1024,
                messages=messages,
            )
            assistant_reply = segunda_respuesta.choices[0].message.content
        else:
            assistant_reply = respuesta.content

        return assistant_reply

    except Exception as e:
        print(f"Error: {e}")
        return "Hubo un error procesando tu mensaje."