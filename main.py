
import asyncio
import os
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton


# Вставь новый токен в переменную окружения BOT_TOKEN
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

if not BOT_TOKEN:
    raise RuntimeError(
        "Укажи токен бота в переменной окружения BOT_TOKEN"
    )

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
)
dp = Dispatcher()

# Координаты городов
CITIES = {
    "Москва": (55.7558, 37.6173),
    "Зеленоград": (55.9919, 37.2144),
    "Санкт-Петербург": (59.9343, 30.3351),
    "Екатеринбург": (56.8389, 60.6057),
    "Поварово": (56.0667, 37.0667),
}

weather_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Москва"),
            KeyboardButton(text="Зеленоград")
        ],
        [
            KeyboardButton(text="Санкт-Петербург"),
            KeyboardButton(text="Екатеринбург")
        ],
        [KeyboardButton(text="Поварово")],
        [KeyboardButton(text="Информация")]
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите город..."
)

# Кэш на 10 минут: данные не будут запрашиваться
# заново при каждом нажатии кнопки.
CACHE_SECONDS = 600
weather_cache = {}

WEATHER_CODES = {
    0: "Ясно ☀️",
    1: "Преимущественно ясно 🌤",
    2: "Переменная облачность ⛅",
    3: "Пасмурно ☁️",
    45: "Туман 🌫",
    48: "Изморозевый туман 🌫",
    51: "Слабая морось 🌦",
    53: "Морось 🌦",
    55: "Сильная морось 🌧",
    61: "Небольшой дождь 🌧",
    63: "Дождь 🌧",
    65: "Сильный дождь 🌧",
    71: "Небольшой снег 🌨",
    73: "Снег ❄️",
    75: "Сильный снег ❄️",
    77: "Снежные зёрна 🌨",
    80: "Ливневый дождь 🌦",
    81: "Сильные ливни 🌧",
    82: "Очень сильные ливни ⛈",
    85: "Снегопад 🌨",
    86: "Сильный снегопад ❄️",
    95: "Гроза ⛈",
    96: "Гроза с градом ⛈",
    99: "Сильная гроза с градом ⛈",
}


async def get_weather(city: str) -> str:
    """Получает текущую погоду и прогноз Open-Meteo."""

    now = datetime.now().timestamp()
    cached = weather_cache.get(city)

    if cached and now - cached["time"] < CACHE_SECONDS:
        return cached["text"]

    latitude, longitude = CITIES[city]

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": (
            "temperature_2m,relative_humidity_2m,"
            "apparent_temperature,weather_code,"
            "pressure_msl,wind_speed_10m"
        ),
        "daily": (
            "temperature_2m_max,temperature_2m_min,"
            "sunrise,sunset"
        ),
        "timezone": "Europe/Moscow",
        "forecast_days": 1,
    }

    url = "https://api.open-meteo.com/v1/forecast"

    timeout = aiohttp.ClientTimeout(total=15)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, params=params) as response:
            response.raise_for_status()
            data = await response.json()

    current = data["current"]
    daily = data["daily"]

    # Исходная температура из погодного API
    real_temp = current["temperature_2m"]

    # Пользовательская поправка: отображаем +2 °C.
    displayed_temp = round(real_temp + 2)

    # Ощущаемая температура также корректируется на +2 °C.
    real_feels = current["apparent_temperature"]
    feels_temp = round(real_feels + 2)

    humidity = current["relative_humidity_2m"]
    pressure = round(current["pressure_msl"])
    wind = current["wind_speed_10m"]
    code = current["weather_code"]

    status = WEATHER_CODES.get(code, "Неизвестные условия")

    sunrise = daily["sunrise"][0].split("T")[-1]
    sunset = daily["sunset"][0].split("T")[-1]

    min_temp = round(daily["temperature_2m_min"][0])
    max_temp = round(daily["temperature_2m_max"][0])

    # Поправка +2 °C применяется только к отображению.
    min_display = min_temp + 2
    max_display = max_temp + 2

    report = (
        f"🌍 *Погода в {city}*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🌡 Температура: *{displayed_temp}°C*\n"
        f"📝 На улице: {status}\n"
        f"🌡 Ощущается как: *{feels_temp}°C*\n"
        f"💧 Влажность: {humidity}%\n"
        f"🧭 Давление: {pressure} гПа\n"
        f"💨 Ветер: {wind} км/ч\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🌅 Восход солнца: *{sunrise}*\n"
        f"🌇 Закат солнца: *{sunset}*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📊 *Прогноз на сегодня*\n"
        f"🌡 Минимум: {min_display}°C\n"
        f"🌡 Максимум: {max_display}°C\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"ℹ️ Температура отображается "
        f"с поправкой +2°C.\n"
        f"🕒 Данные API: {current['time'].split('T')[-1]}"
    )

    weather_cache[city] = {
        "text": report,
        "time": now
    }

    return report


@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "Привет! 🌤 Я погодный бот.\n\n"
        "Выбери город, чтобы узнать погоду, "
        "влажность, ветер, восход и закат солнца.",
        reply_markup=weather_keyboard
    )


@dp.message(F.text == "Информация")
async def send_info(message: Message):
    await message.answer(
        "ℹ️ *Информация о боте*\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🤖 Версия: v0.3\n"
        "💻 Разработчик: Hatik\n
        "🌡 Отображение температуры: +2°C",
        reply_markup=weather_keyboard
    )


@dp.message(Command("weather"))
async def cmd_weather(message: Message):
    args = (message.text or "").split(maxsplit=1)

    if len(args) < 2:
        await message.reply(
            "Укажи город, например:\n"
            "/weather Зеленоград"
        )
        return

    requested_city = args[1].strip().casefold()

    aliases = {
        "питер": "Санкт-Петербург",
        "санкт-петербург": "Санкт-Петербург",
        "санкт петербург": "Санкт-Петербург",
    }

    city = aliases.get(requested_city)

    if city is None:
        city = next(
            (
                name for name in CITIES
                if name.casefold() == requested_city
            ),
            None
        )

    if city is None:
        await message.reply(
            "Город не найден.\n"
            "Доступны: " + ", ".join(CITIES.keys())
        )
        return

    await send_city_weather(message, city)


async def send_city_weather(message: Message, city: str):
    try:
        report = await get_weather(city)
        await message.answer(
            report,
            reply_markup=weather_keyboard
        )
    except (aiohttp.ClientError, KeyError, ValueError) as error:
        print(f"Weather API error: {error}")
        await message.answer(
            "⚠️ Не удалось получить погоду. "
            "Попробуй ещё раз немного позже.",
            reply_markup=weather_keyboard
        )


@dp.message(F.text.in_(set(CITIES.keys())))
async def city_button(message: Message):
    await send_city_weather(message, message.text)


class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is alive")

    def log_message(self, format, *args):
        pass


def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()


async def main():
    threading.Thread(
        target=run_health_server,
        daemon=True
    ).start()

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
