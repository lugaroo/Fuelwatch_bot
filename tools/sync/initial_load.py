#!/usr/bin/env python3
"""
Первоначальная загрузка АЗС из PBF.
Парсит node, way и relation с тегом amenity=fuel.
Использует osmium с locations=True для way/relation.
Путь: Fuelwatch_bot/tools/sync/initial_load.py
"""

import os
import sys
import sqlite3
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]

sys.path.insert(0, str(PROJECT_ROOT))

import osmium
from services.sync_db import init_sync_schema, migrate_schema

# Пути
DB_PATH = PROJECT_ROOT / "stations.db"

PBF_CANDIDATES = [
    PROJECT_ROOT / "russia-latest.osm.pbf",
    PROJECT_ROOT / "fuel.osm.pbf",
]

SOURCE_PBF = None
for candidate in PBF_CANDIDATES:
    if candidate.exists():
        SOURCE_PBF = candidate
        break


class FuelHandler(osmium.SimpleHandler):
    """Обработчик с locations=True — way.nodes содержат координаты."""

    def __init__(self, cursor):
        super().__init__()
        self.cursor = cursor
        self.count = 0
        self.added = 0
        self.updated = 0
        self.skipped = 0
        self.stats = {"node": 0, "way": 0, "relation": 0}

    def _insert_or_update(self, sid, name, brand, lat, lon, obj_type):
        """Вставка или обновление станции."""
        self.cursor.execute("SELECT id FROM stations WHERE id = ?", (sid,))
        if self.cursor.fetchone() is None:
            self.cursor.execute("""
                INSERT INTO stations (id, name, brand, lat, lon, osm_type, active, source)
                VALUES (?, ?, ?, ?, ?, ?, 1, 'pbf')
            """, (sid, name, brand, lat, lon, obj_type))
            self.added += 1
        else:
            self.cursor.execute("""
                UPDATE stations SET
                    name = ?, brand = ?, lat = ?, lon = ?,
                    osm_type = ?, active = 1, source = 'pbf'
                WHERE id = ?
            """, (name, brand, lat, lon, obj_type, sid))
            self.updated += 1
        self.count += 1
        self.stats[obj_type] += 1

    def node(self, n):
        """Обработка node (точка)."""
        if not n.tags or n.tags.get("amenity") != "fuel":
            return
        if not n.location.valid():
            self.skipped += 1
            return

        sid = f"node_{n.id}"
        name = n.tags.get("brand") or n.tags.get("name") or "АЗС"
        brand = n.tags.get("brand", "")

        self._insert_or_update(sid, name, brand, n.location.lat, n.location.lon, "node")

    def way(self, w):
        """Обработка way (полигон/линия).

        С locations=True w.nodes содержит объекты с location.
        """
        if not w.tags or w.tags.get("amenity") != "fuel":
            return

        # Получаем nodes way — они содержат координаты благодаря locations=True
        nodes = list(w.nodes)
        if not nodes:
            self.skipped += 1
            return

        valid_coords = []
        for node in nodes:
            try:
                if node.location.valid():
                    valid_coords.append((node.location.lat, node.location.lon))
            except (AttributeError, RuntimeError):
                # Некоторые nodes могут быть недоступны
                continue

        if not valid_coords:
            self.skipped += 1
            return

        # Центроид = среднее арифметическое
        lat = sum(c[0] for c in valid_coords) / len(valid_coords)
        lon = sum(c[1] for c in valid_coords) / len(valid_coords)

        sid = f"way_{w.id}"
        name = w.tags.get("brand") or w.tags.get("name") or "АЗС"
        brand = w.tags.get("brand", "")

        self._insert_or_update(sid, name, brand, lat, lon, "way")

    def relation(self, r):
        """Обработка relation.

        Для relation используем center из osmium если доступен,
        иначе пропускаем (relations редко содержат amenity=fuel).
        """
        if not r.tags or r.tags.get("amenity") != "fuel":
            return

        # Пробуем получить center relation
        try:
            # Для relation с locations=True members могут иметь location
            members = list(r.members)
            valid_coords = []

            for member in members:
                try:
                    if hasattr(member, 'location') and member.location.valid():
                        valid_coords.append((member.location.lat, member.location.lon))
                except (AttributeError, RuntimeError):
                    continue

            if not valid_coords:
                self.skipped += 1
                return

            lat = sum(c[0] for c in valid_coords) / len(valid_coords)
            lon = sum(c[1] for c in valid_coords) / len(valid_coords)

            sid = f"relation_{r.id}"
            name = r.tags.get("brand") or r.tags.get("name") or "АЗС"
            brand = r.tags.get("brand", "")

            self._insert_or_update(sid, name, brand, lat, lon, "relation")

        except Exception as e:
            self.skipped += 1
            return


def main():
    print("=" * 60)
    print("⛽ ПЕРВОНАЧАЛЬНАЯ ЗАГРУЗКА ИЗ PBF")
    print(f"   Корень проекта: {PROJECT_ROOT}")
    print(f"   БД:  {DB_PATH}")
    print(f"   PBF: {SOURCE_PBF or 'НЕ НАЙДЕН'}")
    print("=" * 60)

    if SOURCE_PBF is None:
        print("❌ PBF-файл не найден. Ожидается один из:")
        for c in PBF_CANDIDATES:
            print(f"   {c}")
        print("\n   Скачайте с: https://download.geofabrik.de/russia.html")
        sys.exit(1)

    print("📐 Инициализация схемы...")
    init_sync_schema()
    migrate_schema()

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    handler = FuelHandler(cur)

    print(f"⏳ Парсинг {SOURCE_PBF.name}...")
    print("   Это может занять 15–40 минут для полного дампа России...")
    print("   (парсим node, way и relation)")

    # ВАЖНО: locations=True позволяет way.nodes иметь координаты
    handler.apply_file(str(SOURCE_PBF), locations=True)

    conn.commit()
    conn.close()

    print(f"\n✅ Готово:")
    print(f"   Всего: {handler.count}")
    print(f"   Nodes: {handler.stats['node']}")
    print(f"   Ways: {handler.stats['way']}")
    print(f"   Relations: {handler.stats['relation']}")
    print(f"   Пропущено (без координат): {handler.skipped}")
    print(f"   Новых: +{handler.added}, Обновлено: ~{handler.updated}")
    print(f"   БД: {DB_PATH}")


if __name__ == "__main__":
    main()
