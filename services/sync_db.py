"""
Работа с БД для синхронизации.
Копируется в: Fuelwatch_bot/services/sync_db.py
"""

import sqlite3
import logging
import json
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# Корень проекта = где лежит bot.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = str(PROJECT_ROOT / "stations.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.row_factory = sqlite3.Row
    return conn


def init_sync_schema():
    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS stations (
            id TEXT PRIMARY KEY,
            name TEXT,
            brand TEXT,
            lat REAL,
            lon REAL,
            osm_type TEXT DEFAULT 'node',
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_sync_at TIMESTAMP,
            source TEXT DEFAULT 'pbf'
        )
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_stations_geo ON stations(lat, lon)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_stations_active ON stations(active)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_stations_sync ON stations(last_sync_at)")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sync_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            finished_at TIMESTAMP,
            regions_total INTEGER,
            regions_success INTEGER,
            stations_added INTEGER,
            stations_updated INTEGER,
            stations_deactivated INTEGER,
            stations_total INTEGER,
            status TEXT DEFAULT 'running',
            error_message TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS station_changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_id TEXT,
            change_type TEXT,
            old_values TEXT,
            new_values TEXT,
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sync_id INTEGER,
            FOREIGN KEY (sync_id) REFERENCES sync_log(id)
        )
    """)

    conn.commit()
    conn.close()
    logger.info("✅ Схема БД инициализирована")


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())


def migrate_schema():
    conn = _connect()
    new_columns = [
        ("brand", "TEXT"),
        ("osm_type", "TEXT DEFAULT 'node'"),
        ("active", "INTEGER DEFAULT 1"),
        ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("last_sync_at", "TIMESTAMP"),
        ("source", "TEXT DEFAULT 'pbf'"),
    ]
    for col_name, col_type in new_columns:
        if not _column_exists(conn, "stations", col_name):
            conn.execute(f"ALTER TABLE stations ADD COLUMN {col_name} {col_type}")
            logger.info(f"➕ Добавлена колонка {col_name}")
    conn.commit()
    conn.close()


def start_sync_log() -> int:
    conn = _connect()
    cur = conn.cursor()
    cur.execute("INSERT INTO sync_log (status) VALUES ('running')")
    sync_id = cur.lastrowid
    conn.commit()
    conn.close()
    return sync_id


def finish_sync_log(sync_id: int, **kwargs):
    conn = _connect()
    cur = conn.cursor()
    status = "error" if kwargs.get("error_message") else "success"
    cur.execute("""
        UPDATE sync_log SET
            finished_at = CURRENT_TIMESTAMP,
            regions_total = ?, regions_success = ?,
            stations_added = ?, stations_updated = ?, stations_deactivated = ?,
            stations_total = ?, status = ?, error_message = ?
        WHERE id = ?
    """, (
        kwargs.get("regions_total", 0), kwargs.get("regions_success", 0),
        kwargs.get("stations_added", 0), kwargs.get("stations_updated", 0),
        kwargs.get("stations_deactivated", 0), kwargs.get("stations_total", 0),
        status, kwargs.get("error_message"), sync_id
    ))
    conn.commit()
    conn.close()
    logger.info(f"📝 Sync #{sync_id} завершён: {status}")


def upsert_stations(stations: List[Dict], sync_id: int, source: str = "overpass") -> Tuple[int, int]:
    conn = _connect()
    cur = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    added, updated = 0, 0

    for st in stations:
        sid = st["id"]
        cur.execute("SELECT id, name, brand, lat, lon, active FROM stations WHERE id = ?", (sid,))
        existing = cur.fetchone()

        if existing is None:
            cur.execute("""
                INSERT INTO stations (id, name, brand, lat, lon, osm_type, active,
                                     created_at, updated_at, last_sync_at, source)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
            """, (sid, st.get("name", "АЗС"), st.get("brand", ""),
                  st["lat"], st["lon"], st.get("osm_type", "node"),
                  now, now, now, source))
            added += 1
            cur.execute("""
                INSERT INTO station_changes (station_id, change_type, new_values, sync_id)
                VALUES (?, 'added', ?, ?)
            """, (sid, json.dumps(st), sync_id))
        else:
            old = dict(existing)
            changed = (
                old.get("name") != st.get("name") or
                old.get("brand") != st.get("brand") or
                abs(old.get("lat", 0) - st["lat"]) > 0.0001 or
                abs(old.get("lon", 0) - st["lon"]) > 0.0001 or
                old.get("active") != 1
            )
            if changed:
                cur.execute("""
                    UPDATE stations SET
                        name = ?, brand = ?, lat = ?, lon = ?, osm_type = ?,
                        active = 1, updated_at = ?, last_sync_at = ?, source = ?
                    WHERE id = ?
                """, (st.get("name", "АЗС"), st.get("brand", ""),
                      st["lat"], st["lon"], st.get("osm_type", "node"),
                      now, now, source, sid))
                updated += 1
                cur.execute("""
                    INSERT INTO station_changes (station_id, change_type, old_values, new_values, sync_id)
                    VALUES (?, 'updated', ?, ?, ?)
                """, (sid, json.dumps(old), json.dumps(st), sync_id))
            else:
                cur.execute("UPDATE stations SET last_sync_at = ? WHERE id = ?", (now, sid))

    conn.commit()
    conn.close()
    return added, updated


def deactivate_old_stations(sync_id: int, cutoff_days: int = 90) -> int:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(f"""
        UPDATE stations SET
            active = 0,
            updated_at = CURRENT_TIMESTAMP
        WHERE source = 'overpass'
          AND active = 1
          AND (last_sync_at IS NULL
               OR datetime(last_sync_at) < datetime('now', '-{cutoff_days} days'))
        RETURNING id
    """)
    deactivated = cur.fetchall()
    count = len(deactivated)
    for row in deactivated:
        cur.execute("""
            INSERT INTO station_changes (station_id, change_type, sync_id)
            VALUES (?, 'deactivated', ?)
        """, (row[0], sync_id))
    conn.commit()
    conn.close()
    if count > 0:
        logger.info(f"🗑 Деактивировано {count} станций")
    return count


def get_sync_stats() -> Dict:
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM sync_log ORDER BY started_at DESC LIMIT 5")
    recent = [dict(row) for row in cur.fetchall()]
    cur.execute("""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN active = 1 THEN 1 ELSE 0 END) as active,
               SUM(CASE WHEN source = 'pbf' THEN 1 ELSE 0 END) as from_pbf,
               SUM(CASE WHEN source = 'overpass' THEN 1 ELSE 0 END) as from_overpass
        FROM stations
    """)
    stats = dict(cur.fetchone())
    conn.close()
    return {"recent_syncs": recent, "stations": stats}
