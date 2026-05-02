import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = "aizen_bot.db"

def get_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Table cache animes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS anime_cache (
            query TEXT PRIMARY KEY,
            data TEXT,
            created_at TIMESTAMP
        )
    ''')
    
    # Table historique conversations IA
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            role TEXT,
            content TEXT,
            timestamp TIMESTAMP
        )
    ''')
    
    # Table téléchargements
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            query TEXT,
            category TEXT,
            url TEXT,
            status TEXT,
            timestamp TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            chat_id INTEGER,
            first_name TEXT,
            username TEXT,
            first_seen TIMESTAMP,
            last_seen TIMESTAMP,
            message_count INTEGER DEFAULT 0,
            callback_count INTEGER DEFAULT 0
        )
    ''')

    # Table favoris anime
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            anime_name TEXT,
            score INTEGER DEFAULT 0,
            added_at TIMESTAMP
        )
    ''')

    # Table rappels
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            chat_id INTEGER,
            message TEXT,
            remind_at TIMESTAMP,
            sent INTEGER DEFAULT 0
        )
    ''')

    conn.commit()
    conn.close()

def cache_anime(query: str, data: dict):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO anime_cache (query, data, created_at) VALUES (?, ?, ?)",
        (query.lower(), json.dumps(data), datetime.now())
    )
    conn.commit()
    conn.close()

def get_cached_anime(query: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT data FROM anime_cache WHERE query = ? AND created_at > ?",
        (query.lower(), datetime.now() - timedelta(days=7))
    )
    row = cursor.fetchone()
    conn.close()
    return json.loads(row[0]) if row else None

def save_conversation(user_id: int, role: str, content: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO conversations (user_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
        (user_id, role, content, datetime.now())
    )
    conn.commit()
    conn.close()

def get_conversation_history(user_id: int, limit: int = 5):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content FROM conversations WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
        (user_id, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    
    history = ""
    for role, content in reversed(rows):
        history += f"{'Utilisateur' if role == 'user' else 'Assistant'}: {content}\n"
    return history

def clear_conversation_history(user_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def save_download_record(user_id: int, query: str, category: str, url: str, status: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO downloads (user_id, query, category, url, status, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, query, category, url, status, datetime.now())
    )
    conn.commit()
    conn.close()

def track_user(
    user_id: int,
    chat_id: int,
    first_name: str = "",
    username: str = "",
    is_callback: bool = False,
):
    conn = get_db()
    cursor = conn.cursor()
    now = datetime.now()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    exists = cursor.fetchone()

    if exists:
        if is_callback:
            cursor.execute(
                """
                UPDATE users
                SET chat_id = ?, first_name = ?, username = ?, last_seen = ?,
                    callback_count = callback_count + 1
                WHERE user_id = ?
                """,
                (chat_id, first_name, username, now, user_id),
            )
        else:
            cursor.execute(
                """
                UPDATE users
                SET chat_id = ?, first_name = ?, username = ?, last_seen = ?,
                    message_count = message_count + 1
                WHERE user_id = ?
                """,
                (chat_id, first_name, username, now, user_id),
            )
    else:
        cursor.execute(
            """
            INSERT INTO users (
                user_id, chat_id, first_name, username, first_seen, last_seen,
                message_count, callback_count
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                chat_id,
                first_name,
                username,
                now,
                now,
                0 if is_callback else 1,
                1 if is_callback else 0,
            ),
        )

    conn.commit()
    conn.close()

def list_user_chat_ids() -> list[int]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT chat_id FROM users WHERE chat_id IS NOT NULL")
    rows = cursor.fetchall()
    conn.close()
    return [int(row[0]) for row in rows if row[0] is not None]

def get_recent_users(limit: int = 5) -> list[dict]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT user_id, first_name, username, message_count, callback_count, last_seen
        FROM users
        ORDER BY last_seen DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "user_id": row[0],
            "first_name": row[1] or "Inconnu",
            "username": row[2] or "",
            "message_count": row[3] or 0,
            "callback_count": row[4] or 0,
            "last_seen": row[5],
        }
        for row in rows
    ]

def get_bot_stats() -> dict:
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT COUNT(*), COALESCE(SUM(message_count), 0), COALESCE(SUM(callback_count), 0)
        FROM users
        """
    )
    users_total, messages_total, callbacks_total = cursor.fetchone()

    cursor.execute("SELECT COUNT(*) FROM conversations")
    conversations_total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM downloads")
    downloads_total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM downloads WHERE status = 'success'")
    downloads_success = cursor.fetchone()[0]

    conn.close()
    return {
        "users_total": users_total or 0,
        "messages_total": messages_total or 0,
        "callbacks_total": callbacks_total or 0,
        "conversations_total": conversations_total or 0,
        "downloads_total": downloads_total or 0,
        "downloads_success": downloads_success or 0,
    }


# ─── Favoris ────────────────────────────────────────────────────────────────

def add_favorite(user_id: int, anime_name: str, score: int = 0) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM favorites WHERE user_id=? AND LOWER(anime_name)=LOWER(?)",
        (user_id, anime_name),
    )
    if cursor.fetchone():
        conn.close()
        return False  # deja en favori
    cursor.execute(
        "INSERT INTO favorites (user_id, anime_name, score, added_at) VALUES (?,?,?,?)",
        (user_id, anime_name, score, datetime.now()),
    )
    conn.commit()
    conn.close()
    return True


def remove_favorite(user_id: int, anime_name: str) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM favorites WHERE user_id=? AND LOWER(anime_name)=LOWER(?)",
        (user_id, anime_name),
    )
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def get_favorites(user_id: int) -> list:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT anime_name, score FROM favorites WHERE user_id=? ORDER BY score DESC, added_at DESC",
        (user_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def update_favorite_score(user_id: int, anime_name: str, score: int) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE favorites SET score=? WHERE user_id=? AND LOWER(anime_name)=LOWER(?)",
        (score, user_id, anime_name),
    )
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated


# ─── Rappels ────────────────────────────────────────────────────────────────

def add_reminder(user_id: int, chat_id: int, message: str, remind_at: datetime) -> int:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO reminders (user_id, chat_id, message, remind_at, sent) VALUES (?,?,?,?,0)",
        (user_id, chat_id, message, remind_at),
    )
    rid = cursor.lastrowid
    conn.commit()
    conn.close()
    return rid


def get_pending_reminders() -> list:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, user_id, chat_id, message FROM reminders WHERE sent=0 AND remind_at <= ?",
        (datetime.now(),),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def mark_reminder_sent(reminder_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE reminders SET sent=1 WHERE id=?", (reminder_id,))
    conn.commit()
    conn.close()
