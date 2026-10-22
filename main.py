import asyncio
import time
import urllib.request
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart, Command

# --- ТВОЙ ТОКЕН TELEGRAM ---
BOT_TOKEN = "8828936622:AAHlaydwIK8qWI82_sLvhRmBz5CHsim5Q4k".strip()

bot = Bot(token=BOT_TOKEN)
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
WEATHER_STATUSES = {
    0: "Ясно ☀️", 1: "Преимущественно ясно 🌤", 2: "Переменная облачность ⛅", 3: "Пасмурно ☁️",
    45: "Туман 🌫", 48: "Осаждающийся туман 🌫", 51: "Легкая морось 🌧", 53: "Умеренная морось 🌧",
    55: "Плотная морось 🌧", 61: "Небольшой дождь 🌧", 63: "Умеренный дождь 🌧", 65: "Сильный дождь 🌧",
    71: "Небольшой снегопад ❄️", 73: "Снегопад ❄️", 75: "Сильный снегопад ☃️", 80: "Кратковременный дождь 🌦",
    81: "Сильный ливневый дождь ⛈", 85: "Небольшой ливневый снег 🌨", 95: "Слабая или умеренная гроза ⚡"
}

# Глобальная память для фиксации погоды на 1 час
weather_memory = {
    "Москва": {"text": None, "updated_at": 0},
    "Зеленоград": {"text": None, "updated_at": 0},
    "Санкт-Петербург": {"text": None, "updated_at": 0},
    "Екатеринбург": {"text": None, "updated_at": 0},
    "Поварово": {"text": None, "updated_at": 0}
}

LIFETIME = 3600  # Время фиксации данных в секундах (1 час)

# Функция реального запроса к метеослужбе по координатам с расчетом восхода/заката
def fetch_real_weather_from_api(city_name: str) -> str:
    if city_name == "Зеленоград":
        lat, lon = 55.98, 37.19
    elif city_name == "Санкт-Петербург":
        lat, lon = 59.93, 30.33
    elif city_name == "Екатеринбург":
        lat, lon = 56.84, 60.61
    elif city_name == "Поварово":
        lat, lon = 56.08, 37.06
    else:
        lat, lon = 55.75, 37.62  # Москва
    
    # Запрашиваем текущие параметры и ежедневные данные (восход и закат)
    url = f"https://open-meteo.com{lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,surface_pressure&daily=sunrise,sunset&timezone=Europe/Moscow"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=6) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                current = data["current"]
                daily = data["daily"]
                
                # 1. Коррекция температуры по твоему ТЗ: берём реальную и ВСЕГДА прибавляем 2 градуса
                base_temp = round(current["temperature_2m"]) + 2
                
                # 2. Ощущается как: строго на 2 градуса меньше от новой базовой температуры
                feels_like = base_temp - 2
                
                # Извлекаем остальные параметры
                humidity = current["relative_humidity_2m"]
                w_code = current["weather_code"]
                wind_speed = round(current["wind_speed_10m"] / 3.6, 1)  # переводим в м/с
                
                # Переводим гПа/гектопаскали давления в привычные мм рт. ст. (умножаем на 0.75006)
                pressure = round(current["surface_pressure"] * 0.75006)
                status = WEATHER_STATUSES.get(w_code, "Переменчивая погода 🌤")
                
                # Извлекаем и форматируем время восхода и заката (убираем лишнюю дату, оставляем ЧЧ:ММ)
                sunrise_time = daily["sunrise"][0].split("T")[1]
                sunset_time = daily["sunset"][0].split("T")[1]
                
                # Рассчитываем суточную сетку диапазонов «минимальная-максимальная»
                range_night = f"{base_temp - 5}–{base_temp - 2}"
                range_morning = f"{base_temp - 2}–{base_temp}"
                range_day = f"{base_temp}–{base_temp + 3}"
                range_evening = f"{base_temp - 3}–{base_temp - 1}"
                
                # Чистый вывод по твоему макету (зачеркнутый текст удален полностью)
                return (
                    f"🌍 Погода в: **{city_name}**\n"
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
                    f"📊 **Ожидаемая температура по времени суток:**\n"
                    f"🌙 Ночью: {range_night}°C\n"
                    f"🌅 Утром: {range_morning}°C\n"
                    f"☀️ Днем: {range_day}°C\n"
                    f"🌆 Вечером: {range_evening}°C\n"
                    f"─────────────────────"
                )
    except Exception as e:
        print(f"Ошибка получения реальной погоды: {e}")
        return None

# Контроль обновления раз в 1 час
def get_cached_weather(city_name: str) -> str:
    current_time = time.time()
    city_data = weather_memory.get(city_name)
    
    if not city_data:
        return None
    
    if city_data["text"] and (current_time - city_data["updated_at"] < LIFETIME):
        return city_data["text"]
    
    new_weather = fetch_real_weather_from_api(city_name)
    
    if new_weather:
        weather_memory[city_name]["text"] = new_weather
        weather_memory[city_name]["updated_at"] = current_time
        return new_weather
    else:
        if city_data["text"]:
            return city_data["text"]
        return "❌ Ошибка: Не удалось обновить метеоданные локации."

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Я твой чистый погодный бот. Выберите город ниже 👇\n"
        "В группах используйте команду формата: `/weather Поварово`",
        reply_markup=weather_keyboard
    )

@dp.message(F.text == "Информация")
async def send_info(message: Message):
    await message.answer(
        "ℹ️ **Информация о боте**\n"
        "─────────────────────\n"
        "🤖 Версия бота: `v0.2`\n"
        "💻 Разработчик: **Hatik**\n"
        "─────────────────────",
        reply_markup=weather_keyboard
    )

@dp.message(Command("weather"))
async def cmd_weather_group(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("❌ Укажите локацию! Пример: `/weather Зеленоград`")
        return
        
    requested_city = args[1].strip().capitalize()
    if requested_city == "Санкт-петербург" or requested_city == "Питер":
        requested_city = "Санкт-Петербург"
        
    if requested_city in weather_memory:
        loop = asyncio.get_event_loop()
        weather_report = await loop.run_in_executor(None, get_cached_weather, requested_city)
        await message.reply(weather_report)
    else:
        await message.reply(f"❌ Локация '{requested_city}' пока не добавлена в код.")

@dp.message(F.text.in_({"Москва", "Зеленоград", "Санкт-Петербург", "Екатеринбург", "Поварово"}))
async def send_weather(message: Message):
    loop = asyncio.get_event_loop()
    weather_report = await loop.run_in_executor(None, get_cached_weather, message.text)
    await message.answer(weather_report, reply_markup=weather_keyboard)

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is alive")

def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

async def main():
    threading.Thread(target=run_health_server, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

