import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Lee la URL de conexión desde la variable de entorno que pusiste en Render
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_connection():
    """Abre una conexión con la base de datos PostgreSQL en Supabase."""
    if not DATABASE_URL:
        raise ValueError("La variable de entorno DATABASE_URL no está configurada.")
    return psycopg2.connect(DATABASE_URL, sslmode="require")


def init_db():
    """Crea las tablas necesarias en PostgreSQL si no existen."""
    conn = get_connection()
    cursor = conn.cursor()

    # Tabla de sesiones
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id VARCHAR(255) PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Tabla de mensajes de historial
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR(255) REFERENCES sessions(session_id) ON DELETE CASCADE,
            role VARCHAR(50) NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.commit()
    cursor.close()
    conn.close()


def ensure_session(session_id):
    """Garantiza que la sesión exista en la tabla 'sessions'."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO sessions (session_id)
        VALUES (%s)
        ON CONFLICT (session_id) DO NOTHING;
    """, (session_id,))

    conn.commit()
    cursor.close()
    conn.close()


def add_message(session_id, role, content):
    """Guarda un nuevo mensaje en el historial."""
    ensure_session(session_id)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO history (session_id, role, content)
        VALUES (%s, %s, %s);
    """, (session_id, role, content))

    conn.commit()
    cursor.close()
    conn.close()


def get_history(session_id):
    """Obtiene el historial de conversaciones para la sesión actual."""
    conn = get_connection()
    # RealDictCursor devuelve los resultados como diccionarios {'role': ..., 'content': ...}
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
        SELECT role, content
        FROM history
        WHERE session_id = %s
        ORDER BY id ASC;
    """, (session_id,))

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    # Convertimos los dicts a formato estándar de Python
    return [{"role": row["role"], "content": row["content"]} for row in rows]


def clear_history(session_id):
    """Elimina el historial de mensajes de la sesión activa."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM history
        WHERE session_id = %s;
    """, (session_id,))

    conn.commit()
    cursor.close()
    conn.close()