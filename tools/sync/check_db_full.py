#!/usr/bin/env python3
"""
Полная диагностика БД — проверяет все таблицы.
"""

import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = str(PROJECT_ROOT / "stations.db")

print("=" * 60)
print("DIAGNOSTICS DB")
print("DB: " + DB_PATH)
print("=" * 60)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [row[0] for row in cur.fetchall()]

print("\nTables (" + str(len(tables)) + "):")
for t in tables:
    print("   * " + t)

required = ["stations", "fuel_status", "user_ids", "activity_log", "sync_log"]
print("\nCheck critical tables:")
for t in required:
    if t in tables:
        print("   OK " + t)
    else:
        print("   MISSING! " + t)

if "fuel_status" not in tables:
    print("\n" + "=" * 60)
    print("WARNING: fuel_status MISSING!")
    print("=" * 60)
    print("Creating fuel_status automatically...")
    cur.execute("CREATE TABLE IF NOT EXISTS fuel_status (station_id TEXT NOT NULL, fuel_type TEXT NOT NULL, status TEXT NOT NULL, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_by INTEGER, PRIMARY KEY (station_id, fuel_type))")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_fuel_status_station ON fuel_status(station_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_fuel_status_time ON fuel_status(updated_at)")
    conn.commit()
    print("OK fuel_status created!")

if "user_ids" not in tables:
    print("\nWARNING: user_ids MISSING! Run init_users_schema() in bot.py")

if "activity_log" not in tables:
    print("\nWARNING: activity_log MISSING! Run init_users_schema() in bot.py")

print("\nStatistics:")
for t in tables:
    try:
        cur.execute("SELECT COUNT(*) FROM " + t)
        count = cur.fetchone()[0]
        print("   * " + t + ": " + str(count) + " rows")
    except:
        print("   * " + t + ": error")

conn.close()
print("\nDone")
