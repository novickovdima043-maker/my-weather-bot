import asyncio
import time
import random
import os
import html
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart, Command

BOT_VERSION = "v0.4"

# --- ТОКЕН TELEGRAM (берётся из переменной окружения BOT_TOKEN на Render) ---
BOT_TOKEN = os.environ.get("8828936622:AAHq6dT_lau4IVa_PdqIL_NMBDmKuNY6qCk", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("Не задана переменная окружения BOT_TOKEN")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Создание нижнего меню с кнопками
weather_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Москва"), KeyboardButton(text="Зеленоград")],
        [KeyboardButton(text="Санкт-Петербург"), KeyboardButton(text="Екатеринбург")],
        [KeyboardButton(text="Поварово")],
        [KeyboardButton(text="Информация")]
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите город или действие..."
)

# Официальные метеорологические статусы
WEATHER_STATUSES = [
    "Ясно ☀️", "Малооблачно 🌤", "Облачно с прояснениями ⛅", "Пасмурно ☁️", "Густой туман 🌫"
]

# Глобальная память для фиксации погоды на 1 час (отдельно для "Сегодня" и "Завтра")
weather_memory = {
    "Москва": {"today": None, "tomorrow": None, "updated_at": 0},
    "Зеленоград": {"today": None, "tomorrow": None, "updated_at": 0},
    "Санкт-Петербург": {"today": None, "tomorrow": None, "updated_at": 0},
    "Екатеринбург": {"today": None, "tomorrow": None, "updated_at": 0},
    "Поварово": {"today": None, "tomorrow": None, "updated_at": 0}
}

LIFETIME = 3600  # Время фиксации данных в секундах (1 час)

# Допустимые варианты написания городов (в нижнем регистре)
CITY_ALIASES = {
    "москва": "Москва",
    "зеленоград": "Зеленоград",
    "поварово": "Поварово",
    "екатеринбург": "Екатеринбург",
    "санкт-петербург": "Санкт-Петербург",
    "питер": "Санкт-Петербург",
    "спб": "Санкт-Петербург",
}


def normalize_city(raw: str):
    return CITY_ALIASES.get(raw.strip().lower())


# Автономный генератор погоды (на базе климатической модели)
def generate_stable_weather(city_name: str, day_type: str = "today") -> str:
    # 1. Задаем базовые климатические температуры и время восхода/заката
    if city_name == "Зеленоград" or city_name == "Поварово":
        # На завтра климатически прогнозируется небольшое похолодание на 1 градус
        real_current_temp = random.randint(1, 4) if day_type == "today" else random.randint(0, 3)
        sunrise_time = "07:18" if day_type == "today" else "07:20"
        sunset_time = "17:12" if day_type == "today" else "17:10"
        humidity = random.randint(82, 94)
    elif city_name == "Санкт-Петербург":
        real_current_temp = random.randint(2, 5) if day_type == "today" else random.randint(1, 4)
        sunrise_time = "07:42" if day_type == "today" else "07:44"
        sunset_time = "17:21" if day_type == "today" else "17:18"
        humidity = random.randint(88, 97)
    elif city_name == "Екатеринбург":
        real_current_temp = random.randint(-3, 1) if day_type == "today" else random.randint(-4, 0)
        sunrise_time = "07:38" if day_type == "today" else "07:40"
        sunset_time = "17:19" if day_type == "today" else "17:16"
        humidity = random.randint(70, 85)
    else:  # Москва
        real_current_temp = random.randint(3, 6) if day_type == "today" else random.randint(2, 5)
        sunrise_time = "07:16" if day_type == "today" else "07:18"
        sunset_time = "17:14" if day_type == "today" else "17:11"
        humidity = random.randint(82, 94)

    # 2. Математические правила Hatik: +2°C к базе, -2°C к ощущениям
    base_temp = real_current_temp + 2
    feels_like = base_temp - 2

    # Рассчитываем суточную сетку диапазонов
    temp_night_min = base_temp - random.randint(4, 5)
    temp_night_max = base_temp - random.randint(2, 3)
    range_night = f"{temp_night_min}–{temp_night_max}"

    temp_morning_min = base_temp - random.randint(2, 3)
    temp_morning_max = base_temp + random.randint(0, 1)
    range_morning = f"{temp_morning_min}–{temp_morning_max}"

    temp_day_min = base_temp - random.randint(0, 1)
    temp_day_max = base_temp + random.randint(2, 3)
    range_day = f"{temp_day_min}–{temp_day_max}"

    temp_evening_min = base_temp - random.randint(3, 4)
    temp_evening_max = base_temp - random.randint(1, 2)
    range_evening = f"{temp_evening_min}–{temp_evening_max}"

    wind_speed = round(random.uniform(2.8, 5.5), 1)
    pressure = random.randint(742, 751)
    status = random.choice(WEATHER_STATUSES)

    day_title = "Сегодня" if day_type == "today" else "Завтра"

    return (
        f"🌍 Погода в: <b>{city_name}</b> ({day_title})\n"
        f"─────────────────────\n"
        f"🌡 Сейчас: {base_temp}°C\n"
        f"🌡 Ощущается как: {feels_like}°C\n"
        f"📝 На улице: {status}\n"
        f"🌅 Восход: {sunrise_time}\n"
        f"🌇 Закат: {sunset_time}\n"
        f"💧 Влажность: {humidity}%\n"
        f"🧭 Давление: {pressure} мм рт. ст.\n"
        f"💨 Ветер: {wind_speed} м/с\n"
        f"─────────────────────\n"
        f"📊 <b>Ожидаемая температура по времени суток:</b>\n"
        f"🌙 Ночью: {range_night}°C\n"
        f"🌅 Утром: {range_morning}°C\n"
        f"☀️ Днем: {range_day}°C\n"
        f"🌆 Вечером: {range_evening}°C\n"
        f"─────────────────────"
    )


# Умная проверка памяти
def get_cached_weather(city_name: str, day_type: str = "today") -> str:
    current_time = time.time()
    city_data = weather_memory.get(city_name)

    if not city_data:
        return None

    # Если 1 час не прошел — выдаем зафиксированный отчет для нужного дня
    if city_data[day_type] and (current_time - city_data["updated_at"] < LIFETIME):
        return city_data[day_type]

    # Генерируем оба отчета заново при истечении часа, чтобы синхронизировать время
    city_data["today"] = generate_stable_weather(city_name, "today")
    city_data["tomorrow"] = generate_stable_weather(city_name, "tomorrow")
    city_data["updated_at"] = current_time

    return city_data[day_type]


# 1. Команда /start
@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        f"Привет! Я твой чистый автономный погодный бот версии {BOT_VERSION}. Выберите город ниже 👇\n"
        "В группах используйте команды:\n"
        "• <code>/weather [город]</code> — погода на сегодня\n"
        "• <code>/tomorrow [город]</code> — погода на завтра",
        reply_markup=weather_keyboard
    )


# 2. Кнопка Информация
@dp.message(F.text == "Информация")
async def send_info(message: Message):
    await message.answer(
        "ℹ️ <b>Информация о боте</b>\n"
        "─────────────────────\n"
        f"🤖 Версия бота: <code>{BOT_VERSION}</code>\n"
        "💻 Разработчик: <b>Hatik</b>\n"
        "─────────────────────",
        reply_markup=weather_keyboard
    )


# Общая логика команд /weather и /tomorrow для групп
async def reply_weather_command(message: Message, day_type: str, example_city: str):
    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2:
        command = "weather" if day_type == "today" else "tomorrow"
        await message.reply(f"❌ Укажите локацию! Пример: <code>/{command} {example_city}</code>")
        return

    city = normalize_city(args[1])
    if city:
        weather_report = get_cached_weather(city, day_type)
        await message.reply(weather_report)
    else:
        await message.reply(f"❌ Локация '{html.escape(args[1].strip())}' пока не добавлена в код.")


# 3. /weather [город] (На сегодня)
@dp.message(Command("weather"))
async def cmd_weather_group(message: Message):
    await reply_weather_command(message, "today", "Зеленоград")


# 4. /tomorrow [город] (На завтра)
@dp.message(Command("tomorrow"))
async def cmd_tomorrow_group(message: Message):
    await reply_weather_command(message, "tomorrow", "Поварово")


# 5. Нажатие Reply-кнопок городов в личных сообщениях (сначала Сегодня, затем Завтра)
@dp.message(F.text.in_({"Москва", "Зеленоград", "Санкт-Петербург", "Екатеринбург", "Поварово"}))
async def send_weather(message: Message):
    weather_today = get_cached_weather(message.text, "today")
    await message.answer(weather_today)

    weather_tomorrow = get_cached_weather(message.text, "tomorrow")
    await message.answer(weather_tomorrow, reply_markup=weather_keyboard)


# --- ХАК ДЛЯ ОБХОДА ОШИБКИ PORT BINDING НА RENDER ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is alive")

    def log_message(self, format, *args):
        pass  # не засоряем логи Render пингами Cron-Job.org


def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()


async def main():
    threading.Thread(target=run_health_server, daemon=True).start()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
