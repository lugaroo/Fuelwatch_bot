# ⛽ FuelWatch

**FuelWatch** — Telegram-бот для поиска ближайших АЗС и проверки наличия топлива.

Пользователь отправляет геолокацию, бот находит ближайшие станции и показывает статус доступности топлива. Данные об АЗС собираются из OpenStreetMap, а информация о наличии топлива обновляется пользователями.

## 🚀 Возможности

- 📍 Поиск ближайших АЗС по геолокации
- ⛽ Статусы АИ-92, АИ-95, АИ-98, АИ-100, ДТ и газа
- 🔄 Обновление статусов топлива пользователями
- 🗺️ Маршрут до выбранной АЗС
- 📊 Административная статистика
- 🔄 Синхронизация базы АЗС с OpenStreetMap
- 🛡️ Обработка ошибок и повторные запросы к внешним API

## 🛠️ Технологии

- Python 3.10+
- aiogram 3
- SQLite
- OpenStreetMap / Overpass API
- osmium
- Chart.js
- Cron / Systemd

## 📁 Структура

    Fuelwatch_bot/
    ├── services/
    │   ├── admin_stats.py
    │   ├── db.py
    │   ├── geo_search.py
    │   ├── overpass_client.py
    │   ├── regions.py
    │   ├── spatial_filter.py
    │   ├── stations_db.py
    │   ├── sync_db.py
    │   └── users_db.py
    ├── tools/
    │   ├── admin/
    │   ├── sync/
    │   ├── generate_report.py
    │   ├── check_db_full.py
    │   ├── initial_load.py
    │   ├── run_sync.py
    │   └── setup_cron.sh
    ├── bot.py
    ├── config.py
    ├── requirements.txt
    └── .env.example

## 📦 Установка

    git clone https://github.com/lugaroo/Fuelwatch_bot.git
    cd Fuelwatch_bot

Создайте виртуальное окружение:

### Windows

    python -m venv .venv
    .venv\Scripts\activate

### Linux / macOS

    python3 -m venv .venv
    source .venv/bin/activate

Установите зависимости:

    pip install -r requirements.txt

Создайте файл `.env` на основе `.env.example` и укажите токен Telegram-бота.

## 🗄️ Создание базы данных

Для работы бота необходима база `stations.db`.

Скачайте актуальный файл `russia-latest.osm.pbf` с OpenStreetMap/Geofabrik и поместите его в корень проекта.

Для обработки PBF необходим `osmium-tool`.

### Ubuntu / WSL

    sudo apt update
    sudo apt install osmium-tool

После этого выполните первоначальную загрузку данных:

    python tools/initial_load.py

После завершения будет создан файл:

    stations.db

Проверить базу можно командой:

    python tools/check_db_full.py

## ▶️ Запуск

После создания `.env` и `stations.db`:

    python bot.py

## 🔄 Синхронизация

Для обновления данных об АЗС используются инструменты из `tools/`:

    tools/
    ├── initial_load.py   # Первоначальная загрузка
    ├── run_sync.py       # Синхронизация данных
    └── check_db_full.py  # Проверка базы

## 🏗️ Архитектура

    OpenStreetMap / Overpass API
                ↓
             tools/
                ↓
           stations.db
                ↓
             bot.py
                ↓
             aiogram
                ↓
             Telegram

## 🔗 GitHub

https://github.com/lugaroo/Fuelwatch_bot