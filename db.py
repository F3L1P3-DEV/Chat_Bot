"""
Capa de base de datos (PostgreSQL / Supabase) para el historial de conversaciones.
--------------------------------------------------------------------------------
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Lee la URL de conexión desde la variable de entorno en Render
DATABASE_URL = os.environ.get("DATABASE_URL")


def get_connection():
    """Abre una conexión con la base de datos PostgreSQL en Supabase."""
    if not DATABASE_URL:
        raise ValueError("La variable de entorno DATABASE_URL no está configurada.")
    return psycopg2.connect(DATABASE_URL, sslmode="require")


def init_db():
    """Crea las tablas en PostgreSQL si no existen."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Tabla de sesiones
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id VARCHAR(255) PRIMARY KEY,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Tabla de mensajes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                session_id VARCHAR(255) NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                role VARCHAR(50) NOT NULL CHECK(role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)

        conn.commit()
        cursor.close()
        conn.close()
        print("--- Base de datos PostgreSQL conectada e inicializada con éxito ---")
    except Exception as e:
        print(f"--- Aviso de conexión a la BD: {e} ---")


def ensure_session(session_id: str):
    """Registra la sesión si es la primera vez que se ve (idempotente)."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO sessions (id)
            VALUES (%s)
            ON CONFLICT (id) DO NOTHING;
        """, (session_id,))

        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error en ensure_session: {e}")


def add_message(session_id: str, role: str, content: str):
    """Guarda un mensaje (del usuario o del asistente) en el historial."""
    ensure_session(session_id)
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO messages (session_id, role, content)
            VALUES (%s, %s, %s);
        """, (session_id, role, content))

        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error en add_message: {e}")


def get_history(session_id):
    """Obtiene el historial de conversaciones para la sesión actual."""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # CAMBIO: Usar 'messages' en lugar de 'history'
    cursor.execute("""
        SELECT role, content
        FROM messages
        WHERE session_id = %s
        ORDER BY id ASC;
    """, (session_id,))

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return [{"role": row["role"], "content": row["content"]} for row in rows]


def clear_history(session_id):
    """Elimina el historial de mensajes de la sesión activa."""
    conn = get_connection()
    cursor = conn.cursor()

    # CAMBIO: Usar 'messages' en lugar de 'history'
    cursor.execute("""
        DELETE FROM messages
        WHERE session_id = %s;
    """, (session_id,))

    conn.commit()
    cursor.close()
    conn.close()