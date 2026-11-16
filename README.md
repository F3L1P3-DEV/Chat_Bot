# 💻 Asistente de Estudio para Devs

Chatbot web que responde preguntas sobre programación, desarrollo web,
Python, AWS y buenas prácticas — pensado como herramienta de estudio
para desarrolladores junior.

Construido con **Flask** (backend) y **HTML/CSS/JavaScript puro** (frontend),
usando la API de **Groq** para generar las respuestas, **Tavily** para la
búsqueda web en vivo y **PostgreSQL (Supabase)** para persistir el historial.

## 🚀 Demo

https://chatbot-s9d3.onrender.com/

## 🛠️ Tecnologías Utilizadas

- **Motor de IA:** Groq API (modelo configurable con `GROQ_MODEL`)
- **Búsqueda web:** Tavily (tool calling)
- **Backend:** Python, Flask, Gunicorn
- **Base de datos:** PostgreSQL en Supabase (psycopg2)
- **Frontend:** HTML5, CSS3, JavaScript (Fetch API + Server-Sent Events)
- **Despliegue:** Render

## ⚙️ Cómo correrlo localmente

1. Clona el repositorio:
   ```bash
   git clone https://github.com/F3L1P3-DEV/Chat_Bot.git
   cd Chat_Bot
   ```

2. Crea un entorno virtual e instala las dependencias:
   ```bash
   python -m venv venv
   source venv/bin/activate   # En Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Copia `.env.example` a `.env` y completa las variables:
   ```bash
   cp .env.example .env
   ```

   | Variable | Obligatoria | Descripción |
   |---|---|---|
   | `SECRET_KEY` | Sí | Clave para firmar la cookie de sesión |
   | `GROQ_API_KEY` | Sí | API key de Groq |
   | `DATABASE_URL` | Sí | Cadena de conexión de Supabase (se recomienda el *Session pooler*) |
   | `TAVILY_API_KEY` | No* | Sin ella la búsqueda web no funciona |
   | `GROQ_MODEL` | No | Por defecto `llama-3.3-70b-versatile` |
   | `COOKIE_SECURE` | No | `1` en producción (HTTPS) |

4. Corre el servidor:
   ```bash
   python app.py
   ```

5. Abre `http://localhost:5000` en tu navegador.

En producción (Render) el comando de inicio es `gunicorn app:app`.

## 📁 Estructura del proyecto

```
Chat_Bot/
├── app.py                  # Backend Flask (rutas, Groq, Tavily)
├── db.py                   # Capa de base de datos (PostgreSQL)
├── templates/index.html    # Interfaz del chat
├── static/
│   ├── style.css           # Estilos
│   ├── script.js           # Lógica del chat en el navegador
│   └── images/             # background.png, principal.png
├── requirements.txt
└── .env.example
```

## 🌱 Posibles mejoras futuras

- Desplegar en AWS (Lambda + API Gateway o Elastic Beanstalk)
- Agregar autenticación de usuarios
- Renderizar Markdown y bloques de código en las respuestas
- Modo oscuro/claro
