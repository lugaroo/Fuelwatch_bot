"""
Минимальный учёт пользователей — только ID, без персональных данных.
Путь: Fuelwatch_bot/services/users_db.py
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = str(PROJECT_ROOT / "stations.db")


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_users_schema():
    """Создаёт минимальные таблицы. Вызвать один раз в main()."""
    conn = _connect()
    cur = conn.cursor()

    # Только ID и метки времени. Никаких имен/ников.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_ids (
            user_id INTEGER PRIMARY KEY,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Лог действий: поиск или обновление
    cur.execute("""
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            activity_type TEXT NOT NULL CHECK(activity_type IN ('search','update')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_activity_user ON activity_log(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_activity_type ON activity_log(activity_type)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_activity_time ON activity_log(created_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_user_ids_seen ON user_ids(last_seen)")

    conn.commit()
    conn.close()


def touch_user(user_id: int):
    """Фиксирует появление пользователя (без имени/ника)."""
    conn = _connect()
    cur = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()

    cur.execute("""
        INSERT INTO user_ids (user_id, first_seen, last_seen)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET last_seen = excluded.last_seen
    """, (user_id, now, now))

    conn.commit()
    conn.close()


def log_activity(user_id: int, activity_type: str):
    """Логирует действие: 'search' или 'update'."""
    conn = _connect()
    cur = conn.cursor()

    # Сначала touch_user, потом лог
    touch_user(user_id)

    cur.execute("""
        INSERT INTO activity_log (user_id, activity_type, created_at)
        VALUES (?, ?, datetime('now'))
    """, (user_id, activity_type))

    conn.commit()
    conn.close()


def get_user_stats() -> dict:
    """Статистика для раздела 'О сервисе'."""
    conn = _connect()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM user_ids")
    total_users = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM activity_log WHERE activity_type = 'update'")
    total_updates = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM activity_log WHERE activity_type = 'search'")
    total_searches = cur.fetchone()[0]

    conn.close()
    return {
        "total_users": total_users,
        "total_updates": total_updates,
        "total_searches": total_searches,
    }
