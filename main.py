import os
import time
import random
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# --- ТОКЕН ТВОЕГО ЕДИНСТВЕННОГО ПОГОДНОГО БОТА ---
BOT_TOKEN = "8828936622:AAHYO1j_x-DTxbUScLKDwlQgKPwAVqoJZT4".strip()
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

CODE_OWNER = "H1A7T0I8K6"
CODE_TECH_ADMIN = "M3I6S8H1K5O4"

bot_status = {"is_active": True}
admin_sessions = {"owner_id": None, "tech_admin_id": None, "is_tech_allowed": True}
user_waiting_for_code = {}

# --- ГЛАВНОЕ REPLY-МЕНЮ ДЛЯ ВСЕХ ---
weather_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
weather_keyboard.row(KeyboardButton("Москва"), KeyboardButton("Зеленоград"))
weather_keyboard.row(KeyboardButton("Санкт-Петербург"), KeyboardButton("Екатеринбург"))
weather_keyboard.row(KeyboardButton("Поварово"))
weather_keyboard.row(KeyboardButton("Информация"), KeyboardButton("⚙️ Система"))

# --- ВИЗУАЛЬНАЯ ИНЛАЙН-ПАНЕЛЬ С ФОТОГРАФИИ ---
def get_inline_admin_panel(user_id):
    status_text = "🔴 Выключить бота" if bot_status["is_active"] else "🟢 Включить бота"
    allowed_text = "🔒 Блокировать тех. админа" if admin_sessions["is_tech_allowed"] else "🔓 Разблокировать тех. админа"
    
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton(text=status_text, callback_data="adm_toggle"))
    
    # Только Владелец (Hatik) видит в своей панели кнопку управления тех. админом
    if user_id == admin_sessions["owner_id"]:
        markup.add(InlineKeyboardButton(text=allowed_text, callback_data="adm_lock_tech"))
        
    markup.add(InlineKeyboardButton(text="🔄 Перезагрузить кэш", callback_data="adm_clear_cache"))
    markup.add(InlineKeyboardButton(text="🚪 Выйти из аккаунта", callback_data="adm_logout"))
    return markup

def get_user_role(user_id):
    if user_id == admin_sessions["owner_id"]: return "owner"
    if user_id == admin_sessions["tech_admin_id"]:
        return "tech_admin" if admin_sessions["is_tech_allowed"] else "blocked"
    return "guest"

# --- ПОГОДНЫЙ МОДУЛЬ (СТРОГО НА СЕГОДНЯ) ---
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

# --- ОБРАБОТКА ХЕНДЛЕРОВ ТЕКСТА ---
@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_waiting_for_code[message.from_user.id] = False
    if not bot_status["is_active"] and get_user_role(message.from_user.id) == "guest":
        bot.send_message(message.chat.id, "⚠️ Бот временно не работает по техническим обстоятельствам")
        return
    bot.send_message(message.chat.id, "Привет! Я твой чистый автономный погодный бот. Выберите город ниже 👇", reply_markup=weather_keyboard)

@bot.message_handler(func=lambda message: message.text == "⚙️ Система")
def process_system_click(message):
    user_id = message.from_user.id
    role = get_user_role(user_id)
    if role in ["owner", "tech_admin"]:
        role_title = "Владелец (Hatik)" if role == "owner" else "Технический администратор"
        bot.send_message(message.chat.id, f"Показываю клавиатуру\nВы вошли как: *{role_title}*", reply_markup=get_inline_admin_panel(user_id))
        return
    user_waiting_for_code[user_id] = True
    bot.send_message(message.chat.id, "🔒 Доступ ограничен. Введите секретную код-фразу для входа в пульт управления:")

@bot.message_handler(func=lambda message: True)
def handle_text_inputs(message):
    user_id = message.from_user.id
    text = message.text.strip()
    
    if user_waiting_for_code.get(user_id):
        if text == CODE_OWNER:
            admin_sessions["owner_id"] = user_id
            user_waiting_for_code[user_id] = False
            bot.send_message(message.chat.id, "Показываю клавиатуру", reply_markup=get_inline_admin_panel(user_id))
        elif text == CODE_TECH_ADMIN:
            if not admin_sessions["is_tech_allowed"]:
                bot.send_message(message.chat.id, "❌ Вход заблокирован Владельцем проекта.")
                user_waiting_for_code[user_id] = False
                return
            admin_sessions["tech_admin_id"] = user_id
            user_waiting_for_code[user_id] = False
            bot.send_message(message.chat.id, "Показываю клавиатуру", reply_markup=get_inline_admin_panel(user_id))
        else:
            bot.send_message(message.chat.id, "❌ Неверная код-фраза. Доступ отклонен.")
            user_waiting_for_code[user_id] = False
        return

    if not bot_status["is_active"] and get_user_role(user_id) == "guest":
        bot.send_message(message.chat.id, "⚠️ Бот временно не работает по техническим обстоятельствам")
        return
        
    if text in weather_memory:
        bot.send_message(message.chat.id, get_cached_weather(text), reply_markup=weather_keyboard)
    elif text == "Информация":
        bot.send_message(message.chat.id, "ℹ *Информация о боте*\n─────────────────────\n🤖 Версия бота: `v4.5`\n💻 Разработчик: *Hatik*\n─────────────────────", reply_markup=weather_keyboard)

# --- МГНОВЕННАЯ ОБРАБОТКА НАЖАТИЙ INLINE-КНОПОК ---
@bot.callback_query_handler(func=lambda call: True)
def process_admin_callbacks(call):
    user_id = call.from_user.id
    role = get_user_role(user_id)
    if role not in ["owner", "tech_admin"]: 
        bot.answer_callback_query(call.id, "❌ Отказано в доступе.")
        return

    if call.data == "adm_toggle":
        bot_status["is_active"] = not bot_status["is_active"]
        status_str = "Бот снова работает" if bot_status["is_active"] else "Бот временно не работает по техническим обстоятельствам"
        # Сразу тушим загрузку часиков на кнопке [1.4]
        bot.answer_callback_query(call.id, f"📢 Состояние изменено!")
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=get_inline_admin_panel(user_id))
        
    elif call.data == "adm_clear_cache":
        for city in weather_memory: weather_memory[city] = {"text": None, "updated_at": 0}
        bot.answer_callback_query(call.id, "🔄 Кэш погодных данных успешно сброшен!", show_alert=True)
        
    elif call.data == "adm_lock_tech":
        if role != "owner": 
            bot.answer_callback_query(call.id, "❌ Доступ закрыт.")
            return
        admin_sessions["is_tech_allowed"] = not admin_sessions["is_tech_allowed"]
        lock_text = "заблокирован" if not admin_sessions["is_tech_allowed"] else "разблокирован"
        bot.answer_callback_query(call.id, f"Технический администратор {lock_text}!", show_alert=True)
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=get_inline_admin_panel(user_id))
        
    elif call.data == "adm_logout":
        if role == "owner": admin_sessions["owner_id"] = None
        elif role == "tech_admin": admin_sessions["tech_admin_id"] = None
        bot.answer_callback_query(call.id, "Сессия закрыта. Выход...")
        # ПОЛНОЕ УДАЛЕНИЕ СООБЩЕНИЯ С КНОПКАМИ С ЭКРАНА ТЕЛЕФОНА! [1.4]
        bot.delete_message(call.message.chat.id, call.message.message_id)

# --- ИЗОЛИРОВАННЫЙ ВЕБ-СЕРВЕР ДЛЯ ПРОХОЖДЕНИЯ ПРОВЕРКИ PORT BINDING ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is alive")

def run_health_server():
