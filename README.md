# FuelWatch ⛽

Telegram-бот для поиска ближайших АЗС и мониторинга наличия топлива.

Пользователь отправляет геолокацию, бот находит ближайшие станции и показывает статус доступности топлива. Данные об АЗС собираются из OpenStreetMap и хранятся в локальной SQLite-базе.

## Возможности

- 📍 Поиск ближайших АЗС по геолокации
- ⛽ Статусы АИ-92, АИ-95, АИ-98, АИ-100, ДТ и газа
- 🔄 Обновление статусов топлива пользователями
- 🗺️ Маршрут до выбранной АЗС
- 📊 Административная статистика
- 🔄 Синхронизация данных с OpenStreetMap
- 🛡️ Retry и обработка ошибок внешних API

## Стек

- Python 3
- aiogram 3
- SQLite
- SQLAlchemy
- OpenStreetMap / Overpass API
- osmium
- Chart.js
- python-dotenv

## Структура

    Fuelwatch_bot/
    ├── services/       # Сервисы БД, API, геоданных и пользователей
    ├── tools/          # Загрузка и синхронизация данных
    ├── bot.py          # Telegram-бот
    ├── config.py       # Конфигурация
    └── requirements.txt

## Установка

    git clone https://github.com/lugaroo/Fuelwatch_bot.git
    cd Fuelwatch_bot
    python -m venv .venv

### Windows

    .venv\Scripts\activate

### Linux / macOS

    source .venv/bin/activate

Установите зависимости:

    pip install -r requirements.txt

Создайте файл `.env` на основе `.env.example` и укажите токен Telegram-бота.

## Создание базы данных

Для работы бота необходим файл `stations.db`.

### 1. Скачать данные OpenStreetMap

Скачайте файл `russia-latest.osm.pbf` с Geofabrik:

https://download.geofabrik.de/russia.html

Поместите файл в корень проекта:

    Fuelwatch_bot/
    ├── russia-latest.osm.pbf
    ├── bot.py
    ├── config.py
    └── ...

### 2. Установить osmium

Ubuntu / WSL:

    sudo apt update
    sudo apt install osmium-tool

### 3. Создать базу

    python tools/initial_load.py

После завершения в корне проекта появится файл:

    stations.db

### 4. Проверить базу

    python tools/check_db_full.py

## Запуск

После создания `stations.db`:

    python bot.py

## Синхронизация данных

Для обновления данных об АЗС используются инструменты в `tools/`:

    tools/
    ├── initial_load.py   # Первоначальное создание базы
    ├── run_sync.py       # Синхронизация данных
    └── check_db_full.py  # Проверка базы

## Архитектура

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

## GitHub

https://github.com/lugaroo/Fuelwatch_bot