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

# Создание нижнего меню с кнопками
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

# Исправленная глобальная память для фиксации погоды строго на Сегодня
weather_memory = {
    "Москва": {"text": None, "updated_at": 0},
    "Зеленоград": {"text": None, "updated_at": 0},
    "Санкт-Петербург": {"text": None, "updated_at": 0},
    "Екатеринбург": {"text": None, "updated_at": 0},
    "Поварово": {"text": None, "updated_at": 0}
}
LIFETIME = 3600

# Автономный генератор одиночной карточки строго на Сегодня
def generate_stable_weather(city_name: str) -> str:
    if city_name in ["Зеленоград", "Поварово"]:
        real_current_temp = random.randint(1, 4)
        sunrise_time = "07:18"
        sunset_time = "17:12"
        humidity = random.randint(82, 94)
    elif city_name == "Санкт-Петербург":
        real_current_temp = random.randint(2, 5)
        sunrise_time = "07:42"
        sunset_time = "17:21"
        humidity = random.randint(88, 97)
    elif city_name == "Екатеринбург":
        real_current_temp = random.randint(-3, 1)
        sunrise_time = "07:38"
        sunset_time = "17:19"
        humidity = random.randint(70, 85)
    else:
        real_current_temp = random.randint(3, 6)  # Москва
        sunrise_time = "07:16"
        sunset_time = "17:14"
        humidity = random.randint(82, 94)
        
    # Математические правила: +2°C к базе, -2°C к ощущениям
    base_temp = real_current_temp + 2
    feels_like = base_temp - 2
    
    # Рассчитываем суточную сетку диапазонов температур
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

    return (
        f"🌍 Погода в: **{city_name}** (Сегодня)\n"
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

def get_cached_weather(city_name: str) -> str:
    current_time = time.time()
    city_data = weather_memory.get(city_name)
    
    # КЭШ: Если 1 час не прошел — выдаем сохраненный текст
    if city_data["text"] and (current_time - city_data["updated_at"] < LIFETIME):
        return city_data["text"]
        
    # Если час прошел — генерируем одну карточку строго на один день
    fresh_report = generate_stable_weather(city_name)
    weather_memory[city_name]["text"] = fresh_report
    weather_memory[city_name]["updated_at"] = current_time
    
    return fresh_report

# ГЛАВНЫЕ СИСТЕМНЫЕ ПЕРЕМЕННЫЕ УПРАВЛЕНИЯ БОТОМ
SYSTEM_STATUS = {"is_active": True}
users_database = set()

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
    await message.answer("Привет! Я твой чистый автономный погодный бот версии v0.4.5. Выберите город ниже 👇", reply_markup=weather_keyboard)

@dp.message(F.text == "Информация")
async def send_info(message: Message):
    if not check_bot_active(message):
        await message.answer("⚠️ Бот временно отключен.")
        return
    await message.answer("ℹ️ **Информация о боте**\n─────────────────────\n🤖 Версия бота: `v0.4.5`\n💻 Разработчик: **Hatik**\n─────────────────────", reply_markup=weather_keyboard)

@dp.message(F.text.in_({"Москва", "Зеленоград", "Санкт-Петербург", "Екатеринбург", "Поварово"}))
async def send_weather(message: Message):
    if not check_bot_active(message):
        await message.answer("⚠️ Бот временно отключен.")
        return
    loop = asyncio.get_event_loop()
    weather_report = await loop.run_in_executor(None, get_cached_weather, message.text)
    await message.answer(weather_report, reply_markup=weather_keyboard)

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
                weather_memory[city] = {"text": None, "updated_at": 0}
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"cleared")
        else:
            self.send_response(404)
            self.end_headers()

def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), RemoteAdminServer)
    server.serve_forever()

async def main():
    threading.Thread(target=run_health_server, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
