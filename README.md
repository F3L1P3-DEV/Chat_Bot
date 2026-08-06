# 💻 Asistente de Estudio para Devs

Chatbot web que responde preguntas sobre programación, desarrollo web,
Python, AWS y buenas prácticas — pensado como herramienta de estudio
para desarrolladores junior.

Construido con **Flask** (backend) y **HTML/CSS/JavaScript puro** (frontend),
usando la API de **Claude (Anthropic)** para generar las respuestas.

## 🚀 Demo

*(agrega aquí el link cuando lo despliegues)*

## 🛠️ Stack

- Python + Flask
- HTML / CSS / JavaScript
- API de Anthropic (Claude)

## ⚙️ Cómo correrlo localmente

1. Clona el repositorio:
   ```bash
   git clone https://github.com/F3L1P3-DEV/dev-assistant-chatbot.git
   cd dev-assistant-chatbot
   ```

2. Crea un entorno virtual e instala las dependencias:
   ```bash
   python -m venv venv
   source venv/bin/activate   # En Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Copia `.env.example` a `.env` y agrega tu API key de Anthropic:
   ```bash
   cp .env.example .env
   ```
   Puedes obtener una key en [console.anthropic.com](https://console.anthropic.com/).

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
