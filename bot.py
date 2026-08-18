import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    CallbackQuery,
)
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import BOT_TOKEN, TELEGRAM_PROXY, SEARCH_DELTA, MAX_RESULTS, FUEL_TYPES
from services.stations_db import get_stations_near, get_station_stats
from services.geo_search import distance_km
from services.db import init_db, get_status, set_status, get_all_statuses
from services.users_db import init_users_schema, touch_user, log_activity, get_user_stats
from services.admin_stats import get_full_stats, generate_html
from aiogram.types import FSInputFile

ADMIN_USER_ID = 301154531

logging.basicConfig(level=logging.INFO)

# Если сервер работает в РФ и Telegram заблокирован на уровне сети,
# укажите TELEGRAM_PROXY в .env, например:
# TELEGRAM_PROXY=http://127.0.0.1:2080
session = AiohttpSession(proxy=TELEGRAM_PROXY) if TELEGRAM_PROXY else None
bot = Bot(token=BOT_TOKEN, session=session)
dp = Dispatcher(storage=MemoryStorage())

ABOUT_TEXT = (
    "⛽ <b>Привет! Я FuelWatch Bot</b>\n\n"
    "Я показываю ближайшие АЗС и актуальную информацию о наличии топлива "
    "по видам: 92, 95, 98, 100, ДТ, Газ.\n\n"
    "🚀 <b>Пока это бета-версия</b>\n"
    "Сервис активно развивается, поэтому некоторые данные могут быть "
    "неточными или устаревшими.\n\n"
    "Каждое обновление от пользователей помогает делиться информацией "
    "точнее для всех водителей.\n\n"
    "Спасибо, что помогаете развивать FuelWatch.\n\n"
)

STATUS_MAP = {
    "fuel:yes": "🟢 есть",
    "fuel:low": "🟡 мало",
    "fuel:no": "🔴 нет",
}
STATUS_UNKNOWN = "❓ неизвестно"


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Найти АЗС", request_location=True)],
            [
                KeyboardButton(text="ℹ️ О сервисе"),
                KeyboardButton(text="📊 Как работает"),
            ],
        ],
        resize_keyboard=True,
    )


def format_station_statuses(station_id: str) -> str:
    """Строит текстовый блок со статусом каждого вида топлива на станции."""
    statuses = get_all_statuses(station_id)
    lines = []
    for ft in FUEL_TYPES:
        row = statuses.get(ft)
        text = row["status"] if row else STATUS_UNKNOWN
        lines.append(f"{ft}: {text}")
    return "\n".join(lines)


def fuel_type_keyboard(updated: set) -> InlineKeyboardMarkup:
    """Клавиатура выбора вида топлива. Уже обновлённые в текущей сессии
    виды помечаются галочкой, чтобы пользователь видел прогресс."""
    buttons, row = [], []
    for i, ft in enumerate(FUEL_TYPES):
        mark = "✅ " if ft in updated else ""
        row.append(InlineKeyboardButton(text=f"{mark}{ft}", callback_data=f"fueltype:{i}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="✅ Готово", callback_data="fueldone")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ---------------- FSM ----------------
class Flow(StatesGroup):
    choosing_station = State()
    choosing_fuel_type = State()
    updating_fuel = State()


# ---------------- START ----------------
@dp.message(F.text == "/start")
async def start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        ABOUT_TEXT + "\n\n👇 Найти АЗС",
        reply_markup=main_keyboard(),
        parse_mode="HTML",
    )


@dp.message(F.text == "ℹ️ О сервисе")
async def about(message: Message):
    touch_user(message.from_user.id)
    stats = get_station_stats()
    user_stats = get_user_stats()

    text = (
        "⛽ <b>FuelWatch</b> — сервис для поиска АЗС и проверки наличия топлива\n\n"
        "📍 <b>Как работает:</b>\n"
        "1. Отправьте свою геолокацию\n"
        "2. Выберите ближайшую АЗС\n"
        "3. Увидите статусы топлива от других водителей\n"
        "4. Обновите статус, если увидели изменения\n\n"

        f"📊 <b>Статистика:</b>\n"
        f"   • АЗС в базе: <b>{stats['active']}</b>\n"
        f"   • Пользователей: <b>{user_stats['total_users']}</b>\n\n"
        f"\n"
        f" ℹ️ Источник: OSM + Overpass API\n\n"
        f" 🛡️ Безопасность: Бот хранит только ID. Личные данные и геолокация не собираются.\n"

    )

    await message.answer(text, parse_mode="HTML")


@dp.message(F.text == "📊 Как работает")
async def how_it_works(message: Message):
    await message.answer(
        "📊 <b>Статусы топлива</b>\n\n"
        "🟢 Есть — топливо доступно\n"
        "🟡 Мало — осталось немного\n"
        "🔴 Нет — топлива нет\n"
        "❓ Неизвестно — данных пока нет\n\n"
        "Статус хранится отдельно для каждого вида топлива "
        "(92, 95, 98, 100, ДТ, Газ) и обновляется самими пользователями.\n"
        "Чем больше обновлений, тем точнее информация.",
        parse_mode="HTML",
    )


# ---------------- GEO ----------------
@dp.message(F.location)
async def geo(message: Message, state: FSMContext):
    touch_user(message.from_user.id)
    log_activity(message.from_user.id, "search")

    lat = message.location.latitude
    lon = message.location.longitude

    nearby = get_stations_near(lat, lon, delta=SEARCH_DELTA)

    results = []
    for sid, name, slat, slon in nearby:
        dist = distance_km(lat, lon, slat, slon)
        results.append((sid, name, slat, slon, dist))

    results.sort(key=lambda x: x[4])
    results = results[:MAX_RESULTS]

    if not results:
        await message.answer("АЗС не найдены поблизости ❌")
        return

    await state.update_data(stations=results, user_lat=lat, user_lon=lon)
    await state.set_state(Flow.choosing_station)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"⛽ {name} ({dist:.1f} км)",
                    callback_data=f"station:{i}",
                )
            ]
            for i, (_, name, _, _, dist) in enumerate(results)
        ]
    )

    await message.answer("Выбери АЗС:", reply_markup=kb)


# ---------------- STATION ----------------
@dp.callback_query(F.data.startswith("station:"), Flow.choosing_station)
async def station(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    idx = int(callback.data.split(":")[1])
    data = await state.get_data()
    stations = data.get("stations")

    if not stations or idx >= len(stations):
        await callback.message.answer("Сессия устарела, отправь геолокацию заново 📍")
        return

    sid, name, slat, slon, dist = stations[idx]

    yandex = (
        f"https://yandex.ru/maps/?rtext="
        f"{data['user_lat']},{data['user_lon']}~{slat},{slon}&rtt=auto"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗺 Маршрут", url=yandex)],
            [InlineKeyboardButton(text="📍 Я приехал", callback_data=f"arrive:{idx}")],
        ]
    )

    await callback.message.answer(
        f"⛽ {name}\n📍 {dist:.1f} км\n\n{format_station_statuses(sid)}",
        reply_markup=kb,
    )


# ---------------- ARRIVE → выбор вида топлива ----------------
@dp.callback_query(F.data.startswith("arrive:"), Flow.choosing_station)
async def arrive(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    idx = int(callback.data.split(":")[1])
    data = await state.get_data()
    stations = data.get("stations")

    if not stations or idx >= len(stations):
        await callback.message.answer("Сессия устарела, отправь геолокацию заново 📍")
        return

    sid, name, *_ = stations[idx]

    await state.update_data(current_station=sid, current_station_name=name, updated_types=[])
    await state.set_state(Flow.choosing_fuel_type)

    await callback.message.answer(
        f"⛽ {name}\n\nВыбери вид топлива:",
        reply_markup=fuel_type_keyboard(updated=set()),
    )


# ---------------- Выбор конкретного вида топлива ----------------
@dp.callback_query(F.data.startswith("fueltype:"), Flow.choosing_fuel_type)
async def fuel_type_chosen(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    idx = int(callback.data.split(":")[1])
    if idx >= len(FUEL_TYPES):
        await callback.message.answer("Ошибка ❌")
        return

    fuel_type = FUEL_TYPES[idx]
    data = await state.get_data()
    sid = data.get("current_station")

    if not sid:
        await callback.message.answer("Сессия устарела, отправь геолокацию заново 📍")
        await state.clear()
        return

    await state.update_data(current_fuel_type=fuel_type)
    await state.set_state(Flow.updating_fuel)

    current = get_status(sid, fuel_type)
    current_text = current["status"] if current else STATUS_UNKNOWN

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🟢 есть", callback_data="fuel:yes"),
                InlineKeyboardButton(text="🟡 мало", callback_data="fuel:low"),
                InlineKeyboardButton(text="🔴 нет", callback_data="fuel:no"),
            ]
        ]
    )

    await callback.message.answer(
        f"⛽ {fuel_type}\nТекущий статус: {current_text}\n\nВыбери актуальный статус:",
        reply_markup=kb,
    )


# ---------------- Сохранение статуса конкретного вида топлива ----------------
@dp.callback_query(F.data.startswith("fuel:"), Flow.updating_fuel)
async def fuel(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    data = await state.get_data()
    sid = data.get("current_station")
    fuel_type = data.get("current_fuel_type")

    if not sid or not fuel_type:
        await callback.message.answer("Сессия потеряна ❌ Попробуй заново.")
        await state.clear()
        return

    status = STATUS_MAP.get(callback.data)
    if not status:
        await callback.message.answer("Ошибка обновления статуса ❌")
        return

    set_status(sid, fuel_type, status, callback.from_user.id)
    log_activity(callback.from_user.id, "update")

    updated_types = set(data.get("updated_types", []))
    updated_types.add(fuel_type)
    await state.update_data(updated_types=list(updated_types))
    await state.set_state(Flow.choosing_fuel_type)

    name = data.get("current_station_name", "АЗС")
    await callback.message.answer(
        f"✅ {fuel_type}: {status}\n\n"
        f"⛽ {name}\n"
        "Выбери следующий вид топлива или нажми «Готово».",
        reply_markup=fuel_type_keyboard(updated=updated_types),
    )


# ---------------- Завершение обновления ----------------
@dp.callback_query(F.data == "fueldone", Flow.choosing_fuel_type)
async def fuel_done(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    data = await state.get_data()
    updated_types = data.get("updated_types", [])
    await state.clear()

    if updated_types:
        text = (
            "✅ Статус обновлён по: " + ", ".join(updated_types) + "\n\n"
            "Спасибо за обновление данных.\n"
            "Это помогает другим водителям.\n\n"
            "📍 Отправь геолокацию для нового поиска АЗС."
        )
    else:
        text = "Ок, ничего не обновляли. 📍 Отправь геолокацию для нового поиска АЗС."

    await callback.message.answer(text, reply_markup=main_keyboard())


@dp.message(F.text == "/admin")
async def admin_cmd(message: Message):
    if message.from_user.id != ADMIN_USER_ID:
        await message.answer("⛔ Доступ запрещён.")
        return

    stats = get_full_stats()

    text = (
        "📊 <b>Админ-панель</b>\n\n"
        f"👥 Пользователей: <b>{stats['total_users']}</b>\n"
        f"   • За 24ч: {stats['active_24h']}\n"
        f"   • За 7д: {stats['active_7d']}\n"
        f"   • За 30д: {stats['active_30d']}\n\n"
        f"⛽ Станций: <b>{stats['active_stations']}</b>\n"
        f"📝 Обновлений: <b>{stats['total_updates']}</b>\n"
        f"🔍 Поисков: <b>{stats['total_searches']}</b>\n\n"
        "Выбери действие:"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 HTML отчёт", callback_data="admin:html")],
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin:refresh")],
        ]
    )

    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@dp.callback_query(F.data.startswith("admin:"))
async def admin_callback(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_USER_ID:
        await callback.answer("⛔", show_alert=True)
        return

    action = callback.data.split(":")[1]

    if action == "html":
        path = generate_html()
        await callback.message.answer_document(
            document=FSInputFile(str(path)),
            caption="✅ HTML отчёт готов"
        )
    elif action == "refresh":
        await admin_cmd(callback.message)

    await callback.answer()

# ---------------- FALLBACK ----------------
@dp.message()
async def fallback(message: Message):
    await message.answer(
        "Не понял 🤔 Нажми «📍 Найти АЗС», чтобы отправить геолокацию.",
        reply_markup=main_keyboard(),
    )


# ---------------- MAIN ----------------
async def main():
    print("BOT STARTED 🚀")
    init_db()
    init_users_schema()  
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())