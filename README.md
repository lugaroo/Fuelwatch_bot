# ⛽ FuelWatch

[![Telegram Bot](https://img.shields.io/badge/Telegram-@fuelwatch_rf_bot-blue?logo=telegram)](https://t.me/fuelwatch_rf_bot)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docker Ready](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker)](https://docker.com)

**FuelWatch** – независимый Telegram-бот для поиска АЗС и проверки наличия топлива в реальном времени.  
Данные собираются самими водителями (краудсорсинг) и обновляются моментально.

---

## 🚀 Возможности

- 📍 **Поиск АЗС по геолокации** – отправьте локацию, получите список ближайших станций с расстоянием.
- ⛽ **Наличие топлива** – 92, 95, 98, 100, ДТ, Газ – статусы обновляются сообществом за 2 тапа.
- 🗺️ **43 000+ АЗС по всей России** – база на основе OpenStreetMap, синхронизация с Overpass API.
- 🧭 **Маршрут до АЗС** – встроенная интеграция с Яндекс.Картами.
- 🔒 **Приватность** – храним только Telegram ID, никаких имён, телефонов или геолокаций.
- 📊 **Админ-статистика** – HTML-отчёт с графиками активности (Chart.js).
- 🔄 **Автообновление базы** – ежемесячная фоновая синхронизация с OSM.

---

## 🛠️ Технологии

- **Python 3.10+** + **aiogram 3.x** (FSM, polling)
- **SQLite** (WAL-режим, индексы)
- **OpenStreetMap** (osmium, PBF, Overpass API)
- **Chart.js** – для админ-отчётов
- **Cron + Systemd** – фоновые задачи
- **Docker** – готовый образ для лёгкого деплоя

---

## 📦 Установка и запуск

### Локально (без Docker)
```bash
git clone https://github.com/lugaroo/Fuelwatch_bot.git
cd FuelWatch
python -m venv venv
source venv/bin/activate  # или venv\Scripts\activate на Windows
pip install -r requirements.txt
# создайте .env с вашим BOT_TOKEN и другими настройками
python bot/main.py
