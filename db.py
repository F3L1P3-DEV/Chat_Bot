"""
Capa de base de datos (SQLite) para el historial de conversaciones.
--------------------------------------------------------------------
Cada visitante del chat tiene su propio session_id (guardado en una
cookie de Flask), así que cada uno ve solo su propio historial.

Tablas:
- sessions: una fila por sesión/visitante.
- messages: cada mensaje (user/assistant) con su session_id, para
  poder reconstruir el historial y mandarlo de vuelta al modelo.
"""

import sqlite3
from datetime import datetime, timezone

DB_PATH = "chat_history.db"


def get_connection():
    """Crea una conexión nueva a la base de datos (SQLite no es
    thread-safe compartiendo una sola conexión, así que abrimos una
    por request)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Crea las tablas si no existen. Se llama una vez al iniciar la app."""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)
    conn.commit()
    conn.close()


def ensure_session(session_id: str):
    """Registra la sesión si es la primera vez que se ve (idempotente)."""
    conn = get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO sessions (id, created_at) VALUES (?, ?)",
        (session_id, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()


def add_message(session_id: str, role: str, content: str):
    """Guarda un mensaje (de usuario o del asistente) en el historial."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (session_id, role, content, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()


def get_history(session_id: str, limit: int = 50):
    """
    Devuelve el historial de una sesión, en formato listo para mandarlo
    a la API de Groq: [{"role": "user"/"assistant", "content": "..."}]

    `limit` acota cuántos mensajes recientes se recuperan, para no
    disparar el tamaño del prompt en conversaciones muy largas.
    """
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT role, content FROM (
            SELECT role, content, created_at, id
            FROM messages
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
        )
        ORDER BY id ASC
        """,
        (session_id, limit),
    ).fetchall()
    conn.close()
    return [{"role": row["role"], "content": row["content"]} for row in rows]


def clear_history(session_id: str):
    """Borra todos los mensajes de una sesión (botón 'Nueva conversación')."""
    conn = get_connection()
    conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()
