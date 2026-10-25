import asyncio
import time
import random
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart, Command

# --- ТВОЙ ОБНОВЛЕННЫЙ ТОКЕН TELEGRAM ПОГОДНОГО БОТА ---
BOT_TOKEN = "8828936622:AAEDwEvUNu7KA0sM_Jv4VNEP8CEalwnOH3g".strip()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ГЛАВНЫЕ СИСТЕМНЫЕ ПЕРЕМЕННЫЕ УПРАВЛЕНИЯ БОТОМ
SYSTEM_STATUS = {"is_active": True}
users_database = set()

weather_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Москва"), KeyboardButton(text="Зеленоград")],
        [KeyboardButton(text="Санкт-Петербург"), KeyboardButton(text="Екатеринбург")],
        [KeyboardButton(text="Поварово")],
        [KeyboardButton(text="Информация")]
    ],
    resize_keyboard=True
)

WEATHER_STATUSES = ["Ясно ☀️", "Малооблачно 🌤", "Облачно с прояснениями ⛅", "Пасмурно ☁️", "Густой туман 🌫"]

weather_memory = {
    "Москва": {"today": None, "tomorrow": None, "updated_at": 0},
    "Зеленоград": {"today": None, "tomorrow": None, "updated_at": 0},
    "Санкт-Петербург": {"today": None, "tomorrow": None, "updated_at": 0},
    "Екатеринбург": {"today": None, "tomorrow": None, "updated_at": 0},
    "Поварово": {"today": None, "tomorrow": None, "updated_at": 0}
}
LIFETIME = 3600

def generate_stable_weather(city_name: str, day_type: str = "today") -> str:
    if city_name in ["Зеленоград", "Поварово"]:
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
    else:
        real_current_temp = random.randint(3, 6) if day_type == "today" else random.randint(2, 5)
        sunrise_time = "07:16" if day_type == "today" else "07:18"
        sunset_time = "17:14" if day_type == "today" else "17:11"
        humidity = random.randint(82, 94)
        
    base_temp = real_current_temp + 2
    feels_like = base_temp - 2
    range_night = f"{base_temp - 5}–{base_temp - 2}"
    range_morning = f"{base_temp - 2}–{base_temp}"
    range_day = f"{base_temp}–{base_temp + 3}"
    range_evening = f"{base_temp - 3}–{base_temp - 1}"
    
    wind_speed = round(random.uniform(2.8, 5.5), 1)
    pressure = random.randint(742, 751)
    status = random.choice(WEATHER_STATUSES)
    day_title = "Сегодня" if day_type == "today" else "Завтра"

    return (
        f"🌍 Погода в: **{city_name}** ({day_title})\n"
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

def get_cached_weather(city_name: str, day_type: str = "today") -> str:
    current_time = time.time()
    city_data = weather_memory.get(city_name)
    if city_data[day_type] and (current_time - city_data["updated_at"] < LIFETIME):
        return city_data[day_type]
    city_data["today"] = generate_stable_weather(city_name, "today")
    city_data["tomorrow"] = generate_stable_weather(city_name, "tomorrow")
    city_data["updated_at"] = current_time
    return city_data[day_type]

def check_bot_active(message: Message) -> bool:
    if not SYSTEM_STATUS["is_active"]:
        return False
    users_database.add(message.from_user.id)
    return True

@dp.message(CommandStart())
async def cmd_start(message: Message):
    if not check_bot_active(message):
        await message.answer("⚠️ Бот временно отключен на техническое обслуживание.")
        return
    await message.answer("Привет! Я твой чистый автономный погодный бот версии v0.4. Выберите город ниже 👇", reply_markup=weather_keyboard)

@dp.message(F.text == "Информация")
async def send_info(message: Message):
    if not check_bot_active(message):
        await message.answer("⚠️ Бот временно отключен.")
        return
    await message.answer("ℹ️ **Информация о боте**\n─────────────────────\n🤖 Версия бота: `v0.4`\n💻 Разработчик: **Hatik**\n─────────────────────", reply_markup=weather_keyboard)

@dp.message(F.text.in_({"Москва", "Зеленоград", "Санкт-Петербург", "Екатеринбург", "Поварово"}))
async def send_weather(message: Message):
    if not check_bot_active(message):
        await message.answer("⚠️ Бот временно отключен.")
        return
    loop = asyncio.get_event_loop()
    weather_today = await loop.run_in_executor(None, get_cached_weather, message.text, "today")
    await message.answer(weather_today)
    weather_tomorrow = await loop.run_in_executor(None, get_cached_weather, message.text, "tomorrow")
    await message.answer(weather_tomorrow, reply_markup=weather_keyboard)

# --- ИНТЕРНЕТ-ШЛЮЗ ДЛЯ ДИСТАНЦИОННОГО УПРАВЛЕНИЯ ИЗ БОТА-ПУЛЬТА ---
class RemoteAdminServer(BaseHTTPRequestHandler):
    def do_GET(self):
        if "/status" in self.path:
            status_str = "active" if SYSTEM_STATUS["is_active"] else "disabled"
            response_json = json.dumps({"status": status_str, "users": len(users_database)})
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(response_json.encode())
            
        elif "/toggle" in self.path:
            SYSTEM_STATUS["is_active"] = not SYSTEM_STATUS["is_active"]
            status_str = "active" if SYSTEM_STATUS["is_active"] else "disabled"
            self.send_response(200)
            self.end_headers()
            self.wfile.write(status_str.encode())
            
        elif "/clear" in self.path:
            for city in weather_memory:
                weather_memory[city] = {"today": None, "tomorrow": None, "updated_at": 0}
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"cleared")
        else:
            self.send_response(404)
            self.end_headers()

def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), RemoteAdminServer)
    server.forever()

async def main():
    threading.Thread(target=run_health_server, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
