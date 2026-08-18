#!/usr/bin/env python3
"""
Генерация отчёта администратора (standalone).
Путь: Fuelwatch_bot/tools/admin/generate_report.py

ИСПОЛЬЗОВАНИЕ:
    python tools/admin/generate_report.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from services.admin_stats import generate_html

def main():
    print("=" * 60)
    print("📊 ГЕНЕРАЦИЯ ОТЧЁТА")
    print("=" * 60)

    path = generate_html()
    print(f"✅ HTML отчёт создан:
   {path}")
    print(f"
💡 Откройте файл в браузере для просмотра.")

if __name__ == "__main__":
    main()
