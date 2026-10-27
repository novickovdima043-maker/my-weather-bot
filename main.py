import os
import time
import random
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# --- ТОКЕН ТВОЕГО ЕДИНСТВЕННОГО ПОГОДНОГО БОТА ---
BOT_TOKEN = "8828936622:AAHYO1j_x-DTxbUScLKDwlQgKPwAVqoJZT4".strip()
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# Настройки текстовых кодов управления
CODE_OWNER_OFF = "H1A7T0I8K6"          # Код выключения для Владельца
CODE_OWNER_ON = "H1A7T0I8K6_ON"        # Код включения для Владельца

CODE_TECH_OFF = "M3I6S8H1K5O4"         # Код выключения для Тех. админа
CODE_TECH_ON = "M3I6S8H1K5O4_ON"       # Код включения для Тех. админа

CODE_BAN_TECH = "BAN_TECH_ADMIN"       # Секретный код Владельца для бана тех. админа
CODE_UNBAN_TECH = "UNBAN_TECH_ADMIN"   # Секретный код Владельца для разбана тех. админа

# Состояние активности системы в оперативной памяти сервера Render
system_status = {"is_active": True, "is_tech_allowed": True}

# --- КЛАВИАТУРА ГОРОДОВ ДЛЯ ОБЫЧНЫХ ЛЮДЕЙ ---
weather_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
weather_keyboard.row(KeyboardButton("Москва"), KeyboardButton("Зеленоград"))
weather_keyboard.row(KeyboardButton("Санкт-Петербург"), KeyboardButton("Екатеринбург"))
weather_keyboard.row(KeyboardButton("Поварово"))
weather_keyboard.row(KeyboardButton("Информация"))

# --- КЛИМАТИЧЕСКАЯ МОДЕЛЬ (ПРОГНОЗ СТРОГО НА СЕГОДНЯ) ---
WEATHER_STATUSES = ["Ясно ☀️", "Малооблачно 🌤", "Облачно с прояснениями ⛅", "Пасмурно ☁️", "Густой туман 🌫"]
weather_memory = {
    "Москва": {"text": None, "updated_at": 0}, "Зеленоград": {"text": None, "updated_at": 0},
    "Санкт-Петербург": {"text": None, "updated_at": 0}, "Екатеринбург": {"text": None, "updated_at": 0},
    "Поварово": {"text": None, "updated_at": 0}
}

def generate_stable_weather(city_name):
    if city_name in ["Зеленоград", "Поварово"]:
        real_current_temp = random.randint(1, 4)
        sunrise_time, sunset_time, humidity = "07:18", "17:12", random.randint(82, 94)
    elif city_name == "Санкт-Петербург":
        real_current_temp = random.randint(2, 5)
        sunrise_time, sunset_time, humidity = "07:42", "17:21", random.randint(88, 97)
    elif city_name == "Екатеринбург":
        real_current_temp = random.randint(-3, 1)
        sunrise_time, sunset_time, humidity = "07:38", "17:19", random.randint(70, 85)
    else:
        real_current_temp = random.randint(3, 6)
        sunrise_time, sunset_time, humidity = "07:16", "17:14", random.randint(82, 94)
        
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
        f"🌍 Погода в: *{city_name}* (Сегодня)\n"
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
        f"📊 *Ожидаемая температура по времени суток:*\n"
        f"🌙 Ночью: {range_night}°C\n"
        f"🌅 Утром: {range_morning}°C\n"
        f"☀️ Днем: {range_day}°C\n"
        f"🌆 Вечером: {range_evening}°C\n"
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

# --- ОБРАБОТКА ХЕНДЛЕРОВ И ТЕКСТОВЫХ СИГНАЛОВ ---
@bot.message_handler(commands=['start'])
def cmd_start(message):
    if not system_status["is_active"]:
        bot.send_message(message.chat.id, "Бот временно не работает по техническим обстоятельствам")
        return
    bot.send_message(message.chat.id, "Привет! Я твой чистый автономный погодный бот. Выберите город ниже 👇", reply_markup=weather_keyboard)

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    text = message.text.strip()

    # 1. СИСТЕМНЫЕ КОДЫ ВЛАДЕЛЦА (Hatik)
    if text == CODE_OWNER_OFF:
        system_status["is_active"] = False
        bot.send_message(message.chat.id, "🔴 Погодный бот успешно ВЫКЛЮЧЕН. Обычные пользователи заблокированы.")
        return
    elif text == CODE_OWNER_ON:
        system_status["is_active"] = True
        bot.send_message(message.chat.id, "🟢 Погодный бот успешно ВКЛЮЧЕН и вернулся в штатный режим.")
        return
    elif text == CODE_BAN_TECH:
        system_status["is_tech_allowed"] = False
        bot.send_message(message.chat.id, "🔒 Доступ для Технического администратора успешно ЗАБЛОКИРОВАН.")
        return
    elif text == CODE_UNBAN_TECH:
        system_status["is_tech_allowed"] = True
        bot.send_message(message.chat.id, "🔓 Доступ для Технического администратора успешно РАЗБЛОКИРОВАН.")
        return

    # 2. СИСТЕМНЫЕ КОДЫ ТЕХНИЧЕСКОГО АДМИНИСТРАТОРА
    if text == CODE_TECH_OFF:
        if not system_status["is_tech_allowed"]:
            bot.send_message(message.chat.id, "❌ Отказано в доступе. Владелец проекта заблокировал ваши права управления.")
            return
        system_status["is_active"] = False
        bot.send_message(message.chat.id, "🔴 Погодный бот успешно ВЫКЛЮЧЕН техническим администратором.")
        return
    elif text == CODE_TECH_ON:
        if not system_status["is_tech_allowed"]:
            bot.send_message(message.chat.id, "❌ Отказано в доступе. Владелец проекта заблокировал ваши права управления.")
            return
        system_status["is_active"] = True
        bot.send_message(message.chat.id, "🟢 Погодный бот успешно ВКЛЮЧЕН техническим администратором.")
        return

    # 3. ПРОВЕРКА ДЛЯ ОБЫЧНЫХ ЛЮДЕЙ
    if not system_status["is_active"]:
        bot.send_message(message.chat.id, "Бот временно не работает по техническим обстоятельствам")
        return

    # 4. ШТАТНАЯ РАБОТА КНОПОК ГОРОДОВ
    if text in weather_memory:
        bot.send_message(message.chat.id, get_cached_weather(text), reply_markup=weather_keyboard)
    elif text == "Информация":
        bot.send_message(message.chat.id, "ℹ *Информация о боте*\n─────────────────────\n🤖 Версия бота: `v4.2`\n💻 Разработчик: *Hatik*\n─────────────────────", reply_markup=weather_keyboard)

# --- ИЗОЛИРОВАННЫЙ ВЕБ-СЕРВЕР ДЛЯ ПРОХОЖДЕНИЯ ПРОВЕРКИ PORT BINDING ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is alive")

def run_health_server():
    # Render передает номер порта в переменные окружения, если его нет - ставим 10000 по умолчанию
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

if __name__ == "__main__":
    # Запускаем веб-заглушку в параллельном потоке, чтобы Render мгновенно считал открытый порт
    threading.Thread(target=run_health_server, daemon=True).start()
    print("🚀 Автономный погодный бот v4.2 со встроенным шлюзом портов запущен!")
    bot.infinity_polling(timeout=20, long_polling_timeout=10)
