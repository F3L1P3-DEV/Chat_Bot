"""
Capa de base de datos (PostgreSQL / Supabase) para el historial de conversaciones.
--------------------------------------------------------------------------------
"""

import os
import logging
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger("chatbot.db")

# Lee la URL de conexión desde la variable de entorno
# (app.py carga el .env antes de importar este módulo).
DATABASE_URL = os.environ.get("DATABASE_URL")


def get_connection():
    """Abre una conexión con la base de datos PostgreSQL en Supabase."""
    if not DATABASE_URL:
        raise ValueError("La variable de entorno DATABASE_URL no está configurada.")
    return psycopg2.connect(DATABASE_URL, sslmode="require", connect_timeout=10)


@contextmanager
def get_cursor(dict_rows=False):
    """
    Entrega un cursor dentro de una transacción:
    confirma (commit) si todo sale bien, revierte (rollback) ante un error
    y SIEMPRE cierra cursor y conexión, sin dejar conexiones abiertas.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor) if dict_rows else conn.cursor()
        try:
            yield cursor
            conn.commit()
        finally:
            cursor.close()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        conn.close()


def init_db():
    """Crea las tablas en PostgreSQL si no existen."""
    try:
        with get_cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id VARCHAR(255) PRIMARY KEY,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(255) NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                    role VARCHAR(50) NOT NULL CHECK(role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
            # Acelera la consulta del historial por sesión
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_session_id
                ON messages (session_id, id);
            """)
        logger.info("Base de datos PostgreSQL conectada e inicializada con éxito.")
    except Exception:
        logger.exception("No se pudo inicializar la base de datos")


def ensure_session(session_id: str):
    """Registra la sesión si es la primera vez que se ve (idempotente)."""
    with get_cursor() as cursor:
        cursor.execute("""
            INSERT INTO sessions (id)
            VALUES (%s)
            ON CONFLICT (id) DO NOTHING;
        """, (session_id,))


def add_message(session_id: str, role: str, content: str):
    """Guarda un mensaje (del usuario o del asistente) en el historial."""
    ensure_session(session_id)
    with get_cursor() as cursor:
        cursor.execute("""
            INSERT INTO messages (session_id, role, content)
            VALUES (%s, %s, %s);
        """, (session_id, role, content))


def add_exchange(session_id: str, user_content: str, assistant_content: str):
    """
    Guarda la pregunta y su respuesta en UNA sola transacción:
    o se guardan ambas o ninguna (evita mensajes huérfanos).
    """
    ensure_session(session_id)
    with get_cursor() as cursor:
        cursor.execute("""
            INSERT INTO messages (session_id, role, content)
            VALUES (%s, 'user', %s);
        """, (session_id, user_content))
        cursor.execute("""
            INSERT INTO messages (session_id, role, content)
            VALUES (%s, 'assistant', %s);
        """, (session_id, assistant_content))


def get_history(session_id: str, limit: int | None = None):
    """
    Obtiene el historial de la sesión en orden cronológico.
    Si se indica `limit`, devuelve solo los últimos `limit` mensajes.
    """
    query = """
        SELECT role, content
        FROM messages
        WHERE session_id = %s
        ORDER BY id DESC
    """
    params = [session_id]
    if limit:
        query += " LIMIT %s"
        params.append(limit)

    with get_cursor(dict_rows=True) as cursor:
        cursor.execute(query, params)
        rows = cursor.fetchall()

    rows.reverse()  # de más antiguo a más reciente
    return [{"role": row["role"], "content": row["content"]} for row in rows]


def clear_history(session_id: str):
    """Elimina el historial de mensajes de la sesión activa."""
    with get_cursor() as cursor:
        cursor.execute("DELETE FROM messages WHERE session_id = %s;", (session_id,))
