import asyncio
import time
import random
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import CommandStart

# --- ТОКЕН ТВОЕГО ЕДИНСТВЕННОГО ПОГОДНОГО БОТА ---
BOT_TOKEN = "8828936622:AAF17VoASomT32uFfX8XHhts7HOfUqwGjV4".strip()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Секретные код-фразы доступа
CODE_OWNER = "H1A7T0I8K6"
CODE_TECH_ADMIN = "M3I6S8H1K5O4"

# ГЛАВНЫЕ ПЕРЕМЕННЫЕ УПРАВЛЕНИЯ БОТОМ
bot_status = {"is_active": True}

# База авторизованных сессий (сохраняется в памяти до перезапуска сервера)
admin_sessions = {
    "owner_id": None,             # Telegram ID Владельца (Hatik)
    "tech_admin_id": None,        # Telegram ID Технического администратора
    "is_tech_allowed": True       # Флаг: Разрешен ли доступ тех. админу
}

# Текущее состояние ожидания пароля пользователем
user_waiting_for_code = {}

# =====================================================================
# --- КЛАВИАТУРЫ И ИНТЕРФЕЙС СИСТЕМЫ ---
# =====================================================================
# Главное Reply-меню кнопок (Добавлена кнопка Система)
weather_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Москва"), KeyboardButton(text="Зеленоград")],
        [KeyboardButton(text="Санкт-Петербург"), KeyboardButton(text="Екатеринбург")],
        [KeyboardButton(text="Поварово")],
        [KeyboardButton(text="Информация"), KeyboardButton(text="⚙️ Система")]
    ],
    resize_keyboard=True
)

# Инлайновая админ-панель (Строго как на фото, без статистики, с Выходом)
def get_inline_admin_panel(user_id):
    status_text = "🔴 Выключить бота" if bot_status["is_active"] else "🟢 Включить бота"
    allowed_text = "🔒 Блокировать тех. админа" if admin_system_status_allowed(user_id) else "🔓 Разблокировать тех. админа"
    
    keyboard_buttons = [
        [InlineKeyboardButton(text=status_text, callback_data="adm_toggle")],
        [InlineKeyboardButton(text="🔄 Перезагрузить кэш", callback_data="adm_clear_cache")]
    ]
    
    # Только Владелец (Hatik) видит инлайн-кнопку бана тех. админа
    if user_id == admin_sessions["owner_id"]:
        keyboard_buttons.append([InlineKeyboardButton(text=allowed_text, callback_data="adm_lock_tech")])
        
    # Кнопка Выхода присутствует всегда в самом низу
    keyboard_buttons.append([InlineKeyboardButton(text="🚪 Выйти из аккаунта", callback_data="adm_logout")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

def admin_system_status_allowed(user_id):
    return admin_sessions["is_tech_allowed"]

# Проверка роли текущего пользователя
def get_user_role(user_id):
    if user_id == admin_sessions["owner_id"]:
        return "owner"
    if user_id == admin_sessions["tech_admin_id"]:
        if admin_sessions["is_tech_allowed"]:
            return "tech_admin"
        return "blocked"
    return "guest"

# Проверка глобальной активности бота для обычных людей
def is_bot_available_for_user(user_id):
    role = get_user_role(user_id)
    if role in ["owner", "tech_admin"]:
        return True  # Администрация имеет доступ к кнопкам всегда
    return bot_status["is_active"]

# =====================================================================
# --- ЛОГИКА ПОГОДНОГО МОДУЛЯ ---
# =====================================================================
WEATHER_STATUSES = ["Ясно ☀️", "Малооблачно 🌤", "Облачно с прояснениями ⛅", "Пасмурно ☁️", "Густой туман 🌫"]

weather_memory = {
    "Москва": {"text": None, "updated_at": 0}, "Зеленоград": {"text": None, "updated_at": 0},
    "Санкт-Петербург": {"text": None, "updated_at": 0}, "Екатеринбург": {"text": None, "updated_at": 0},
    "Поварово": {"text": None, "updated_at": 0}
}
LIFETIME = 3600

def generate_stable_weather(city_name: str) -> str:
    if city_name in ["Зеленоград", "Поварово"]:
        real_current_temp = random.randint(1, 4)
        sunrise_time = "07:18"; sunset_time = "17:12"; humidity = random.randint(82, 94)
    elif city_name == "Санкт-Петербург":
        real_current_temp = random.randint(2, 5)
        sunrise_time = "07:42"; sunset_time = "17:21"; humidity = random.randint(88, 97)
    elif city_name == "Екатеринбург":
        real_current_temp = random.randint(-3, 1)
        sunrise_time = "07:38"; sunset_time = "17:19"; humidity = random.randint(70, 85)
    else:
        real_current_temp = random.randint(3, 6)
        sunrise_time = "07:16"; sunset_time = "17:14"; humidity = random.randint(82, 94)
        
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

# =====================================================================
# --- ОБРАБОТКА ДЕЙСТВИЙ И КОМАНД БОТА ---
# =====================================================================

@dp.message(CommandStart())
async def cmd_start(message: Message):
    if not is_bot_available_for_user(message.from_user.id):
        await message.answer("⚠️ Бот выключен по техническим обстоятельствам")
        return
    user_waiting_for_code[message.from_user.id] = False
    await message.answer("Привет! Я твой чистый автономный погодный бот версии v2.5. Выберите город ниже 👇", reply_markup=weather_keyboard)

# Нажатие на кнопку Система
@dp.message(F.text == "⚙️ Система")
async def process_system_click(message: Message):
    user_id = message.from_user.id
    role = get_user_role(user_id)
    
    # Если админ уже авторизован — просто выкатываем ему пульт заново
    if role in ["owner", "tech_admin"]:
        role_title = "Владелец (Hatik)" if role == "owner" else "Технический администратор"
        await message.answer(f"🎛 Панель управления активна!\nВы вошли как: **{role_title}**", reply_markup=get_inline_admin_panel(user_id))
        return
        
    user_waiting_for_code[user_id] = True
    await message.answer("🔒 Доступ ограничен. Введите секретную код-фразу для входа в панель управления:")

# Обработка ввода текстового пароля
@dp.message(F.text)
async def handle_text_inputs(message: Message):
    user_id = message.from_user.id
    text = message.text.strip()
    
    # Проверяем, ждет ли бот от этого юзера ввода секретного кода
    if user_waiting_for_code.get(user_id):
        if text == CODE_OWNER:
            admin_sessions["owner_id"] = user_id
            user_waiting_for_code[user_id] = False
            await message.answer("👑 Авторизация успешна! Добро пожаловать, Владелец (Hatik).", reply_markup=get_inline_admin_panel(user_id))
            return
        elif text == CODE_TECH_ADMIN:
            if not admin_sessions["is_tech_allowed"]:
                await message.answer("❌ Вход заблокирован. Владелец проекта закрыл доступ для технических администраторов.")
                user_waiting_for_code[user_id] = False
                return
            admin_sessions["tech_admin_id"] = user_id
            user_waiting_for_code[user_id] = False
            await message.answer("🛠 Авторизация успешна! Доступ предоставлен Техническому администратору.", reply_markup=get_admin_keyboard_or_panel_inline(user_id))
            return
        else:
            await message.answer("❌ Неверная код-фраза. Доступ отклонен. Попробуйте еще раз или выберите город на кнопках:")
            user_waiting_for_code[user_id] = False
            return

    # Обычная логика кнопок городов
    if not is_bot_available_for_user(user_id):
        await message.answer("⚠️ Бот выключен по техническим обстоятельствам")
        return
        
    if text in weather_memory:
        loop = asyncio.get_event_loop()
        weather_report = await loop.run_in_executor(None, get_cached_weather, text)
        await message.answer(weather_report, reply_markup=weather_keyboard)
    elif text == "Информация":
        await message.answer("ℹ️ **Информация о боте**\n─────────────────────\n🤖 Версия бота: `v2.5`\n💻 Разработчик: **Hatik**\n─────────────────────", reply_markup=weather_keyboard)

def get_admin_keyboard_or_panel_inline(user_id):
    return get_inline_admin_panel(user_id)

# =====================================================================
# --- ЛОГИКА НАЖАТИЙ НА INLINE-КНОПКИ ПАНЕЛИ (CALLBACK QUERIES) ---
# =====================================================================
@dp.callback_query()
async def process_admin_callbacks(callback: CallbackQuery):
    user_id = callback.from_user.id
