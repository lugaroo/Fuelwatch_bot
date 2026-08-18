import sqlite3
from config import DB_PATH, FUEL_TYPES


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _migrate_legacy_schema(conn):
    """Если в БД осталась старая таблица fuel_status (один статус на
    станцию, без колонки fuel_type) — переименовываем её в бэкап и
    освобождаем имя под новую схему."""
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(fuel_status)")
    columns = {row[1] for row in cur.fetchall()}

    if columns and "fuel_type" not in columns:
        cur.execute("ALTER TABLE fuel_status RENAME TO fuel_status_legacy_backup")
        conn.commit()
        print(
            "⚠️  Обнаружена старая схема fuel_status (без fuel_type). "
            "Старые данные сохранены в таблице fuel_status_legacy_backup."
        )


def _add_user_id_column(conn):
    """Миграция: добавляет user_id в fuel_status, если отсутствует."""
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(fuel_status)")
    columns = {row[1] for row in cur.fetchall()}

    if columns and "user_id" not in columns:
        cur.execute("ALTER TABLE fuel_status ADD COLUMN user_id INTEGER")
        conn.commit()
        print("➕ Добавлена колонка user_id в fuel_status")


def init_db():
    conn = _connect()
    _migrate_legacy_schema(conn)

    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fuel_status (
            station_id TEXT NOT NULL,
            fuel_type TEXT NOT NULL,
            status TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_id INTEGER,
            PRIMARY KEY (station_id, fuel_type)
        )
    """)

    _add_user_id_column(conn)  # ← миграция для существующих таблиц

    conn.commit()
    conn.close()


def set_status(station_id: str, fuel_type: str, status: str, user_id: int):
    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO fuel_status (station_id, fuel_type, status, user_id)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(station_id, fuel_type)
        DO UPDATE SET
            status = excluded.status,
            user_id = excluded.user_id,
            updated_at = CURRENT_TIMESTAMP
    """, (str(station_id), fuel_type, status, user_id))

    conn.commit()
    conn.close()


def get_status(station_id: str, fuel_type: str):
    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT status, updated_at, user_id
        FROM fuel_status
        WHERE station_id = ? AND fuel_type = ?
    """, (str(station_id), fuel_type))

    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    return {"status": row[0], "updated_at": row[1], "user_id": row[2]}


def get_all_statuses(station_id: str) -> dict:
    """Возвращает {fuel_type: {"status", "updated_at", "user_id"} | None}"""
    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT fuel_type, status, updated_at, user_id
        FROM fuel_status
        WHERE station_id = ?
    """, (str(station_id),))

    existing = {
        r[0]: {"status": r[1], "updated_at": r[2], "user_id": r[3]}
        for r in cur.fetchall()
    }
    conn.close()

    return {ft: existing.get(ft) for ft in FUEL_TYPES}