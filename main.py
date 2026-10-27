import os
import time
import random
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# --- ТОКЕН ТВОЕГО ПОГОДНОГО БОТА ---
BOT_TOKEN = "8828936622:AAHYO1j_x-DTxbUScLKDwlQgKPwAVqoJZT4".strip()
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# --- ГЛАВНОЕ REPLY-МЕНЮ ДЛЯ ВСЕХ ---
weather_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
weather_keyboard.row(KeyboardButton("Москва"), KeyboardButton("Зеленоград"))
weather_keyboard.row(KeyboardButton("Санкт-Петербург"), KeyboardButton("Екатеринбург"))
weather_keyboard.row(KeyboardButton("Поварово"))
weather_keyboard.row(KeyboardButton("Информация"))

WEATHER_STATUSES = ["Ясно ☀️", "Малооблачно 🌤", "Облачно с прояснениями ⛅", "Пасмурно ☁️", "Густой туман 🌫"]

# Глобальная память кэша погоды (фиксация на 1 час)
weather_memory = {
    "Москва": {"text": None, "updated_at": 0}, "Зеленоград": {"text": None, "updated_at": 0},
    "Санкт-Петербург": {"text": None, "updated_at": 0}, "Екатеринбург": {"text": None, "updated_at": 0},
    "Поварово": {"text": None, "updated_at": 0}
}

# Автономный суточный генератор карточки "Сегодня + Завтра"
def generate_stable_weather(city_name):
    # Задаем базовые температуры регионов для конца октября
    if city_name in ["Зеленоград", "Поварово"]:
        current_base = random.randint(1, 4)
        sunrise, sunset = "07:18", "17:12"
    elif city_name == "Санкт-Петербург":
        current_base = random.randint(2, 5)
        sunrise, sunset = "07:42", "17:21"
    elif city_name == "Екатеринбург":
        current_base = random.randint(-3, 1)
        sunrise, sunset = "07:38", "17:19"
    else:
        current_base = random.randint(3, 6) # Москва
        sunrise, sunset = "07:16", "17:14"
        
    humidity = random.randint(80, 95)
    pressure = random.randint(742, 752)
    wind_speed = round(random.uniform(2.5, 5.0), 1)
    status_today = random.choice(WEATHER_STATUSES)
    status_tomorrow = random.choice(WEATHER_STATUSES)
    
    # Расчет диапазонов времени суток для Сегодня
    base_today = current_base + 2
    feels_today = base_today - 2
    range_night_today = f"{base_today - 4}–{base_today - 2}"
    range_day_today = f"{base_temp - 1 if 'base_temp' in locals() else base_today}–{base_today + 3}"
    
    # Расчет диапазонов времени суток для Завтра (сдвиг климатического фронта)
    base_tomorrow = current_base + random.choice([-1, 0, 1]) + 2
    feels_tomorrow = base_tomorrow - 2
    range_night_tomorrow = f"{base_tomorrow - 4}–{base_tomorrow - 2}"
    range_day_tomorrow = f"{base_tomorrow}–{base_tomorrow + 3}"

    return (
        f"🌍 Погода в: *{city_name}*\n"
        f"─────────────────────\n"
        f"☀️ **СЕГОДНЯ:**\n"
        f"🌡 Сейчас: {base_today}°C (Ощущается как {feels_today}°C)\n"
        f"📝 На улице: {status_today}\n"
        f"🌅 Восход: {sunrise} | Закат: {sunset}\n"
        f"💧 Влажность: {humidity}% | 🧭 Давление: {pressure} мм\n"
        f"💨 Ветер: {wind_speed} м/с\n"
        f"🌙 Ночью: {range_night_today}°C | ☀️ Днем: {range_day_today}°C\n"
        f"─────────────────────\n"
        f"🔮 **ЗАВТРА:**\n"
        f"🌡 Температура: {base_tomorrow}°C (Ощущается как {feels_tomorrow}°C)\n"
        f"📝 Прогноз: {status_tomorrow}\n"
        f"🌙 Ночью: {range_night_tomorrow}°C | ☀️ Днем: {range_day_tomorrow}°C\n"
        f"─────────────────────"
    )

def get_cached_weather(city_name):
    current_time = time.time()
    city_data = weather_memory.get(city_name)
    if city_data["text"] and (current_time - city_data["updated_at"] < 3600):
        return city_data["text"]
    fresh_report = generate_stable_weather(city_name)
    weather_memory[city_name]["text"] = fresh_report
    weather_memory[city_name]["updated_at"] = current_time
    return fresh_report

# --- ОБРАБОТКА КОМАНД И НАЖАТИЙ ---
@bot.message_handler(commands=['start'])
def cmd_start(message):
    bot.send_message(message.chat.id, "Привет! Я твой чистый автономный погодный бот. Выберите город ниже 👇", reply_markup=weather_keyboard)

@bot.message_handler(func=lambda message: True)
def handle_text_inputs(message):
    text = message.text.strip()
    
    if text in weather_memory:
        bot.send_message(message.chat.id, get_cached_weather(text), reply_markup=weather_keyboard)
    elif text == "Информация":
        bot.send_message(message.chat.id, "ℹ *Информация о боте*\n─────────────────────\n🤖 Версия бота: `v5.0`\n💻 Разработчик: *Hatik*\n─────────────────────", reply_markup=weather_keyboard)

# --- ВЕБ-ЗАГЛУШКА ДЛЯ ПРОХОЖДЕНИЯ ПРОВЕРКИ PORT BINDING RENDER ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is live")

def run_bot_polling():
    bot.infinity_polling(timeout=20, long_polling_timeout=10)

if __name__ == "__main__":
    # Запуск веб-интерфейса на основном потоке для мгновенного отклика Render
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    
    # Запуск бота в изолированном фоновом потоке
    threading.Thread(target=run_bot_polling, daemon=True).start()
    
    print(f"🌍 Сервер портов успешно запущен на порту {port}!")
    server.serve_forever()
