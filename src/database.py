"""
Módulo de gestión de base de datos para el historial de conversaciones.
"""
import sqlite3
from typing import List, Tuple


def init_database():
    """Inicializa la base de datos SQLite para el historial de conversaciones."""
    conn = sqlite3.connect('data/chat_history.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            role TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id INTEGER PRIMARY KEY,
            preferences TEXT,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()


def save_message(user_id: int, message: str, role: str):
    """Guarda un mensaje en el historial."""
    conn = sqlite3.connect('data/chat_history.db')
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO chat_history (user_id, message, role) VALUES (?, ?, ?)',
        (user_id, message, role)
    )
    conn.commit()
    conn.close()


def get_chat_history(user_id: int, limit: int = 10) -> str:
    """Obtiene el historial reciente de un usuario."""
    conn = sqlite3.connect('data/chat_history.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT message, role, timestamp 
        FROM chat_history 
        WHERE user_id = ? 
        ORDER BY timestamp DESC 
        LIMIT ?
    ''', (user_id, limit))
    messages = cursor.fetchall()
    conn.close()
    
    # Invertir para tener orden cronológico
    messages.reverse()
    
    # Formatear para el agente
    formatted_history = []
    for msg, role, timestamp in messages:
        if role == "user":
            formatted_history.append(f"Usuario: {msg}")
        else:
            formatted_history.append(f"CAL-E: {msg}")
    
    return "\n".join(formatted_history)


def clear_old_history(user_id: int, keep_last: int = 50):
    """Limpia el historial antiguo, manteniendo solo los últimos N mensajes."""
    conn = sqlite3.connect('data/chat_history.db')
    cursor = conn.cursor()
    cursor.execute('''
        DELETE FROM chat_history 
        WHERE user_id = ? 
        AND id NOT IN (
            SELECT id FROM chat_history 
            WHERE user_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        )
    ''', (user_id, user_id, keep_last))
    conn.commit()
    conn.close()


def delete_user_history(user_id: int) -> int:
    """Borra todo el historial de un usuario. Retorna el número de registros eliminados."""
    conn = sqlite3.connect('data/chat_history.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM chat_history WHERE user_id = ?', (user_id,))
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted_count
