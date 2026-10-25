import asyncio
import time
import random
import os
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart

# --- ТОКЕН ТВОЕГО ПОГОДНОГО БОТА ---
BOT_TOKEN = "8828936622:AAEDwEvUNu7KA0sM_Jv4VNEP8CEalwnOH3g".strip()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ГЛАВНЫЕ СИСТЕМНЫЕ ПЕРЕМЕННЫЕ УПРАВЛЕНИЯ БОТОМ
SYSTEM_STATUS = {"is_active": True}
LAST_OWNER_ID = {"id": None}  # Запоминаем ID владельца для отправки уведомлений

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
    "Москва": {"text": None, "updated_at": 0},
    "Зеленоград": {"text": None, "updated_at": 0},
    "Санкт-Петербург": {"text": None, "updated_at": 0},
    "Екатеринбург": {"text": None, "updated_at": 0},
    "Поварово": {"text": None, "updated_at": 0}
}
LIFETIME = 3600

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
        real_current_temp = random.randint(3, 6)
        sunrise_time = "07:16"
        sunset_time = "17:14"
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
    if city_data["text"] and (current_time - city_data["updated_at"] < LIFETIME):
        return city_data["text"]
    fresh_report = generate_stable_weather(city_name)
    weather_memory[city_name]["text"] = fresh_report
    weather_memory[city_name]["updated_at"] = current_time
    return fresh_report

@dp.message(CommandStart())
async def cmd_start(message: Message):
    LAST_OWNER_ID["id"] = message.from_user.id  # Ловим ID для пульта
    if not SYSTEM_STATUS["is_active"]:
        await message.answer("⚠️ Бот временно отключен на техническое обслуживание.")
        return
    await message.answer("Привет! Я твой чистый автономный погодный бот версии v0.7. Выберите город ниже 👇", reply_markup=weather_keyboard)

@dp.message(F.text == "Информация")
async def send_info(message: Message):
    if not SYSTEM_STATUS["is_active"]:
        await message.answer("⚠️ Бот временно отключен на техническое обслуживание.")
        return
    await message.answer("ℹ️ **Информация о боте**\n─────────────────────\n🤖 Версия бота: `v0.7`\n💻 Разработчик: **Hatik**\n─────────────────────", reply_markup=weather_keyboard)

@dp.message(F.text.in_({"Москва", "Зеленоград", "Санкт-Петербург", "Екатеринбург", "Поварово"}))
async def send_weather(message: Message):
    if not SYSTEM_STATUS["is_active"]:
        await message.answer("⚠️ Бот временно отключен на техническое обслуживание.")
        return
    loop = asyncio.get_event_loop()
    weather_report = await loop.run_in_executor(None, get_cached_weather, message.text)
    await message.answer(weather_report, reply_markup=weather_keyboard)

# --- ЗАЩИЩЕННЫЙ КАНАЛ СВЯЗИ ДЛЯ КОВЕРТНОГО БОТА УПРАВЛЕНИЯ ---
class SecureAdminGateway(BaseHTTPRequestHandler):
    def do_POST(self):
        # Проверяем секретный заголовок, чтобы никто чужой не смог управлять
        auth_header = self.headers.get("Authorization")
        if auth_header != "Bearer HatikSecretKey2026":
            self.send_response(401)
            self.end_headers()
            return

        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        data = json.loads(body)
        action = data.get("action")

        # Создаем отдельный асинхронный поток для отправки уведомления в Telegram
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        if action == "toggle":
            SYSTEM_STATUS["is_active"] = not SYSTEM_STATUS["is_active"]
            status_str = "active" if SYSTEM_STATUS["is_active"] else "disabled"
            
            # Погодный бот сам пишет нужный русский текст в чат по команде пульта
            if LAST_OWNER_ID["id"]:
                msg_text = "Бот снова работает" if SYSTEM_STATUS["is_active"] else "Бот выключен по техническим обстоятельствам"
                loop.run_until_complete(bot.send_message(chat_id=LAST_OWNER_ID["id"], text=msg_text))

            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(status_str.encode())

        elif action == "clear":
            for city in weather_memory:
                weather_memory[city] = {"text": None, "updated_at": 0}
            if LAST_OWNER_ID["id"]:
                loop.run_until_complete(bot.send_message(chat_id=LAST_OWNER_ID["id"], text="🔄 Кэш погодных данных на сервере успешно сброшен!"))
            
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"cleared")
        else:
            self.send_response(400)
            self.end_headers()

def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SecureAdminGateway)
    server.serve_forever()

async def main():
    threading.Thread(target=run_health_server, daemon=True).start()
    print("🚀 Погодный бот v0.7 запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
