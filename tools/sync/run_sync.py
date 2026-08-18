#!/usr/bin/env python3
"""
Запуск Overpass-синхронизации.
Путь: Fuelwatch_bot/tools/sync/run_sync.py
"""

import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import time
import logging
import argparse
from datetime import datetime, timezone

from services.regions import get_all_regions
from services.overpass_client import fetch_fuel_stations
from services.sync_db import (
    init_sync_schema, migrate_schema, start_sync_log, finish_sync_log,
    upsert_stations, deactivate_old_stations, get_sync_stats,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("overpass_sync")


def run_sync(dry_run: bool = False, region_filter=None, skip_deactivation: bool = False) -> bool:
    logger.info("=" * 60)
    logger.info("🚀 СИНХРОНИЗАЦИЯ Overpass → SQLite")
    logger.info(f"🕐 {datetime.now(timezone.utc).isoformat()}")
    logger.info("=" * 60)

    init_sync_schema()
    migrate_schema()

    regions = get_all_regions()
    if region_filter:
        regions = [(n, b) for n, b in regions if n in region_filter]

    total = len(regions)
    logger.info(f"📍 Регионов: {total}")

    sync_id = start_sync_log()
    logger.info(f"📝 Sync ID: {sync_id}")

    success_count = 0
    total_added, total_updated = 0, 0
    errors = []

    try:
        for i, (name, bbox) in enumerate(regions, 1):
            logger.info(f"
[{i}/{total}] 🌍 {name}")
            if dry_run:
                logger.info("   🧪 [DRY RUN]")
                continue
            try:
                stations = fetch_fuel_stations(bbox)
                if not stations:
                    logger.warning(f"   ⚠️ Нет данных")
                    continue
                added, updated = upsert_stations(stations, sync_id, source="overpass")
                total_added += added
                total_updated += updated
                logger.info(f"   ✅ +{added} ~{updated} (всего {len(stations)})")
                success_count += 1
                time.sleep(1)
            except Exception as e:
                logger.error(f"   ❌ {e}")
                errors.append(f"{name}: {e}")
                continue

        deactivated = 0
        if not dry_run and not skip_deactivation:
            logger.info("
🗑 Деактивация устаревших...")
            deactivated = deactivate_old_stations(sync_id, cutoff_days=90)

        stats = get_sync_stats()
        total_stations = stats["stations"]["total"]

        logger.info("
" + "=" * 60)
        logger.info("✅ ЗАВЕРШЕНО")
        logger.info(f"   Регионов: {success_count}/{total}")
        logger.info(f"   Добавлено: {total_added}, Обновлено: {total_updated}")
        logger.info(f"   Деактивировано: {deactivated}")
        logger.info(f"   Всего в БД: {total_stations}")
        logger.info("=" * 60)

        finish_sync_log(
            sync_id=sync_id,
            regions_total=total,
            regions_success=success_count,
            stations_added=total_added,
            stations_updated=total_updated,
            stations_deactivated=deactivated,
            stations_total=total_stations,
            error_message="; ".join(errors) if errors else None,
        )
        return len(errors) == 0

    except Exception as e:
        logger.exception("💥 Критическая ошибка")
        finish_sync_log(sync_id=sync_id, error_message=str(e))
        return False


def main():
    parser = argparse.ArgumentParser(description="Синхронизация АЗС")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--regions", nargs="+")
    parser.add_argument("--skip-deactivation", action="store_true")
    parser.add_argument("--stats", action="store_true")
    args = parser.parse_args()

    if args.stats:
        stats = get_sync_stats()
        print("
📊 СТАТИСТИКА")
        print("-" * 40)
        s = stats["stations"]
        print(f"Всего: {s['total']} | Активных: {s['active']}")
        print(f"Из PBF: {s['from_pbf']} | Из Overpass: {s['from_overpass']}")
        print("
Последние синхронизации:")
        for sync in stats["recent_syncs"]:
            st = "✅" if sync["status"] == "success" else "❌"
            print(f"  {st} #{sync['id']} | {sync['started_at']} | {sync['status']}")
        return

    success = run_sync(
        dry_run=args.dry_run,
        region_filter=args.regions,
        skip_deactivation=args.skip_deactivation,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
