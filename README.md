# 💻 Asistente de Estudio para Devs

Chatbot web que responde preguntas sobre programación, desarrollo web,
Python, AWS y buenas prácticas — pensado como herramienta de estudio
para desarrolladores junior.

Construido con **Flask** (backend) y **HTML/CSS/JavaScript puro** (frontend),
usando la API de **Groq** para generar las respuestas.

## 🚀 Demo

https://chatbot-s9d3.onrender.com/

## 🛠️ Tecnologías Utilizadas
Motor de IA: Groq API (Llama 3 / Mixtral)

Backend: Python, Flask, Gunicorn

Frontend: HTML5, CSS3, JavaScript (Fetch API)

Despliegue: Render

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

3. Copia `.env.example` a `.env` y agrega tu API key de Groq:
   ```bash
   cp .env.example .env
   ```

4. Corre el servidor:
   ```bash
   python app.py
   ```

5. Abre `http://localhost:5000` en tu navegador.

## 📁 Estructura del proyecto

```
dev-assistant-chatbot/
├── app.py                  # Backend Flask
├── templates/index.html    # Interfaz del chat
├── static/style.css        # Estilos
├── static/script.js        # Lógica del chat en el navegador
├── requirements.txt
└── .env.example
```

## 🌱 Posibles mejoras futuras

- Desplegar en AWS (Lambda + API Gateway o Elastic Beanstalk)
- Persistir el historial de conversación en una base de datos
- Agregar autenticación de usuarios
- Modo oscuro/claro
