import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан в .env")

# Путь к базе данных считается от корня проекта, а не от текущей
# рабочей директории — раньше относительный путь "data/stations.db"
# ломался при запуске бота не из корня проекта.
DB_PATH = str(BASE_DIR / "stations.db")

# Прокси для доступа к api.telegram.org, если сервер физически
# находится в РФ и сам нуждается в VPN/прокси для исходящих соединений.
# Пример в .env: TELEGRAM_PROXY=http://127.0.0.1:2080
# или:            TELEGRAM_PROXY=socks5://127.0.0.1:1080
TELEGRAM_PROXY = os.getenv("TELEGRAM_PROXY") or None

# Радиус поиска ближайших АЗС в градусах (~0.5 ≈ 55 км по широте)
SEARCH_DELTA = float(os.getenv("SEARCH_DELTA", "0.5"))

# Сколько ближайших станций показывать пользователю
MAX_RESULTS = int(os.getenv("MAX_RESULTS", "10"))

# Виды топлива, по которым отслеживается статус на каждой АЗС.
# Порядок влияет на то, как кнопки выбора вида топлива будут
# расположены в боте.
FUEL_TYPES = ["92", "95", "98", "100", "ДТ", "Газ"]