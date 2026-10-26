import asyncio
import time
import random
import os
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart, Command

# --- ТОКЕН ТВОЕГО ПОГОДНОГО БОТА ---
BOT_TOKEN = "8828936622:AAF17VoASomT32uFfX8XHhts7HOfUqwGjV4".strip()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ГЛАВНЫЕ СИСТЕМНЫЕ ПЕРЕМЕННЫЕ УПРАВЛЕНИЯ БОТОМ
SYSTEM_STATUS = {"is_active": True}

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

WEATHER_STATUSES = [
    "Ясно ☀️", "Малооблачно 🌤", "Облачно с прояснениями ⛅", "Пасмурно ☁️", "Густой туман 🌫"
]

weather_memory = {
    "Москва": {"text": None, "updated_at": 0},
    "Зеленоград": {"text": None, "updated_at": 0},
    "Санкт-Петербург": {"text": None, "updated_at": 0},
    "Екатеринбург": {"text": None, "updated_at": 0},
    "Поварово": {"text": None, "updated_at": 0}
}
LIFETIME = 3600

def generate_stable_weather(city_name: str) -> str:
    if city_name == "Зеленоград" or city_name == "Поварово":
        base_temp = random.randint(2, 5)
        humidity = random.randint(82, 94)
    elif city_name == "Санкт-Петербург":
        base_temp = random.randint(3, 6)
        humidity = random.randint(88, 97)
    elif city_name == "Екатеринбург":
        base_temp = random.randint(-2, 2)
        humidity = random.randint(70, 85)
    else:
        base_temp = random.randint(4, 7)  # Москва
        humidity = random.randint(82, 94)
        
    temp_night_min = base_temp - random.randint(4, 5)
    temp_night_max = base_temp - random.randint(2, 3)
    range_night = f"{temp_night_min}–{temp_night_max}"
    
    temp_morning_min = base_temp - random.randint(2, 3)
    temp_morning_max = base_temp + random.randint(0, 1)
    range_morning = f"{temp_morning_min}–{range_morning}"
    
    temp_day_min = base_temp - random.randint(0, 1)
    temp_day_max = base_temp + random.randint(2, 3)
    range_day = f"{temp_day_min}–{temp_day_max}"
    
    temp_evening_min = base_temp - random.randint(3, 4)
    temp_evening_max = base_temp - random.randint(1, 2)
    range_evening = f"{temp_evening_min}–{temp_evening_max}"
    
    wind_speed = round(random.uniform(2.8, 5.5), 1)
    pressure = random.randint(742, 751)
    status = random.choice(WEATHER_STATUSES)

    return (
        f"🌍 Погода в: **{city_name}** (Сегодня)\n"
        f"─────────────────────\n"
        f"🌡 Сейчас: {base_temp}°C\n"
        f"📝 На улице: {status}\n"
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

def get_cached_weather(city_name: str) -> str:
    current_time = time.time()
    city_data = weather_memory.get(city_name)
    if city_data["text"] and (current_time - city_data["updated_at"] < LIFETIME):
        return city_data["text"]
    new_weather = generate_stable_weather(city_name)
    weather_memory[city_name]["text"] = new_weather
    weather_memory[city_name]["updated_at"] = current_time
    return new_weather

def check_bot_active() -> bool:
    return SYSTEM_STATUS["is_active"]

@dp.message(CommandStart())
async def cmd_start(message: Message):
    if not check_bot_active():
        await message.answer("⚠️ Бот выключен по техническим обстоятельствам")
        return
    await message.answer("Привет! Я твой чистый автономный погодный бот. Выберите город ниже 👇", reply_markup=weather_keyboard)

@dp.message(F.text == "Информация")
async def send_info(message: Message):
    if not check_bot_active():
        await message.answer("⚠️ Бот выключен по техническим обстоятельствам")
        return
    await message.answer("ℹ️ **Информация о боте**\n─────────────────────\n🤖 Версия бота: `v0.2`\n💻 Разработчик: **Hatik**\n─────────────────────", reply_markup=weather_keyboard)

@dp.message(Command("weather"))
async def cmd_weather_group(message: Message):
    if not check_bot_active():
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("❌ Укажите локацию! Пример: `/weather Зеленоград`")
        return
    requested_city = args[1].strip().capitalize()
    if requested_city in ["Санкт-петербург", "Питер"]:
        requested_city = "Санкт-Петербург"
        
    if requested_city in weather_memory:
        loop = asyncio.get_event_loop()
        weather_report = await loop.run_in_executor(None, get_cached_weather, requested_city)
        await message.reply(weather_report)
    else:
        await message.reply(f"❌ Локация '{requested_city}' пока не добавлена в код.")

@dp.message(F.text.in_({"Москва", "Зеленоград", "Санкт-Петербург", "Екатеринбург", "Поварово"}))
async def send_weather(message: Message):
    if not check_bot_active():
        await message.answer("⚠️ Бот выключен по техническим обстоятельствам")
        return
    loop = asyncio.get_event_loop()
    weather_report = await loop.run_in_executor(None, get_cached_weather, message.text)
    await message.answer(weather_report, reply_markup=weather_keyboard)

# --- ИСТОРИЧЕСКИЙ СЕТЕВОЙ ШЛЮЗ ДЛЯ ПУЛЬТА УПРАВЛЕНИЯ ---
class RemoteAdminGateway(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        data = json.loads(body)
        action = data.get("action")

        if action == "toggle":
            SYSTEM_STATUS["is_active"] = not SYSTEM_STATUS["is_active"]
            status_str = "active" if SYSTEM_STATUS["is_active"] else "disabled"
            self.send_response(200)
            self.end_headers()
            self.wfile.write(status_str.encode())
        elif action == "clear":
            for city in weather_memory:
                weather_memory[city] = {"text": None, "updated_at": 0}
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"cleared")
        else:
            self.send_response(400)
            self.end_headers()

def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), RemoteAdminGateway)
    server.serve_forever()

async def main():
    threading.Thread(target=run_health_server, daemon=True).start()
    print("🚀 Исторический погодный бот успешно запущен на Render!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
