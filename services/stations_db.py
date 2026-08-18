import sqlite3
from pathlib import Path

# Корень проекта = где лежит bot.py (на один уровень выше services/)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = str(PROJECT_ROOT / "stations.db")


def _connect():
    return sqlite3.connect(DB_PATH)


def get_all_stations():
    """ВСЕ станции (включая неактивные). Только для служебных задач."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT id, name, lat, lon, active, source FROM stations")
    rows = cur.fetchall()
    conn.close()
    return rows


def get_stations_near(lat: float, lon: float, delta: float = 0.5, active_only: bool = True):
    """
    Поиск станций в прямоугольнике.
    По умолчанию показывает только активные (active=1).
    """
    conn = _connect()
    cur = conn.cursor()

    if active_only:
        cur.execute("""
            SELECT id, name, lat, lon
            FROM stations
            WHERE active = 1
              AND lat BETWEEN ? AND ?
              AND lon BETWEEN ? AND ?
        """, (lat - delta, lat + delta, lon - delta, lon + delta))
    else:
        cur.execute("""
            SELECT id, name, lat, lon
            FROM stations
            WHERE lat BETWEEN ? AND ?
              AND lon BETWEEN ? AND ?
        """, (lat - delta, lat + delta, lon - delta, lon + delta))

    rows = cur.fetchall()
    conn.close()
    return rows


def get_station_by_id(station_id: str):
    """Получить станцию по ID (включая неактивные)."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name, brand, lat, lon, osm_type, active, source
        FROM stations
        WHERE id = ?
    """, (str(station_id),))
    row = cur.fetchone()
    conn.close()
    return row


def get_station_stats() -> dict:
    """Статистика по станциям в БД."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN active = 1 THEN 1 ELSE 0 END) as active,
               SUM(CASE WHEN source = 'pbf' THEN 1 ELSE 0 END) as from_pbf,
               SUM(CASE WHEN source = 'overpass' THEN 1 ELSE 0 END) as from_overpass
        FROM stations
    """)
    row = cur.fetchone()
    conn.close()
    return {
        "total": row[0] or 0,
        "active": row[1] or 0,
        "from_pbf": row[2] or 0,
        "from_overpass": row[3] or 0,
    }
