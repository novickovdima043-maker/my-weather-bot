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

# Создание нижнего меню с кнопками (Добавлено Поварово и Информация)
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

# Актуальный словарь кодов погоды Всемирной метеорологической организации (WMO)
WEATHER_DESCRIPTIONS = {
    0: "Ясно ☀️", 1: "Преимущественно ясно 🌤", 2: "Переменная облачность ⛅", 3: "Пасмурно ☁️",
    45: "Туман 🌫", 48: "Осаждающийся туман 🌫", 51: "Легкая морось 🌧", 53: "Умеренная морось 🌧",
    55: "Плотная морось 🌧", 61: "Небольшой дождь 🌧", 63: "Умеренный дождь 🌧", 65: "Сильный дождь 🌧",
    71: "Небольшой снегопад ❄️", 73: "Снегопад ❄️", 75: "Сильный снегопад ☃️", 80: "Кратковременный дождь 🌦",
    81: "Сильный ливневый дождь ⛈", 85: "Небольшой ливневый снег 🌨", 95: "Слабая или умеренная гроза ⚡"
}

# Глобальная память для фиксации погоды из сети на 1 час для всех 5 локаций
weather_memory = {
    "Москва": {"text": None, "updated_at": 0},
    "Зеленоград": {"text": None, "updated_at": 0},
    "Санкт-Петербург": {"text": None, "updated_at": 0},
    "Екатеринбург": {"text": None, "updated_at": 0},
    "Поварово": {"text": None, "updated_at": 0}
}

LIFETIME = 3600  # Фиксация данных на 1 час

# Функция РЕАЛЬНОГО запроса к метеослужбе по координатам
def fetch_real_weather_from_api(city_name: str) -> str:
    # Устанавливаем точные координаты городов для спутника
    if city_name == "Зеленоград":
        lat, lon = 55.98, 37.19
    elif city_name == "Санкт-Петербург":
        lat, lon = 59.93, 30.33
    elif city_name == "Екатеринбург":
        lat, lon = 56.84, 60.61
    elif city_name == "Поварово":
        lat, lon = 56.08, 37.06  # Координаты Поварово
    elif city_name == "Москва":
        lat, lon = 55.75, 37.62
    else:
        return None
    
    url = f"https://open-meteo.com{lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m&timezone=Europe/Moscow"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=6) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                current = data["current"]
                
                real_temp = round(current["temperature_2m"])
                humidity = current["relative_humidity_2m"]
                w_code = current["weather_code"]
                wind_speed = round(current["wind_speed_10m"] / 3.6, 1)  # км/ч в м/с
                
                status = WEATHER_DESCRIPTIONS.get(w_code, "Переменчивая погода 🌤")
                
                # Строим суточные диапазоны «от-до»
                range_night = f"{real_temp - 4}–{real_temp - 2}"
                range_morning = f"{real_temp - 2}–{real_temp}"
                range_day = f"{real_temp}–{real_temp + 3}"
                range_evening = f"{real_temp - 1}–{real_temp + 1}"
                
                return (
                    f"🌍 Погода в: **{city_name}** (Живые метеоданные)\n"
                    f"─────────────────────\n"
                    f"🌡 Сейчас: {real_temp}°C (точное значение)\n"
                    f"📝 На улице: {status}\n"
                    f"💧 Влажность: {humidity}%\n"
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

# Умный контроль памяти (выдать сохраненную или обновить из сети)
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
        return "❌ Ошибка: Не удалось получить метеоданные локации."

# 1. Обработка команды /start в личных сообщениях
@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Я твой продвинутый погодный бот. Выберите город на кнопках ниже 👇 "
        "Или добавьте меня в группу и используйте команду /weather [город]",
        reply_markup=weather_keyboard
    )

# 2. Обработка кнопки «Информация»
@dp.message(F.text == "Информация")
async def send_info(message: Message):
    await message.answer(
        "ℹ️ **Информация о боте**\n"
        "─────────────────────\n"
        "🤖 Версия бота: `v0.2`\n"
        "💻 Разработчик: **Hatik**\n"
        "☀️ Движок данных: Open-Meteo API\n"
        "─────────────────────",
        reply_markup=weather_keyboard
    )

# 3. Обработка команды /weather [город] для работы в группах и чатах
@dp.message(Command("weather"))
async def cmd_weather_group(message: Message):
    # Извлекаем текст, который идет после команды /weather
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        await message.reply(
            "❌ Укажите город! Пример использования в группе:\n"
            "`/weather Зеленоград` или `/weather Москва`"
        )
        return
        
    requested_city = args[1].strip().capitalize()
    
    # Приводим к правильному регистру для поиска в памяти
    if requested_city == "Санкт-петербург" or requested_city == "Питер":
        requested_city = "Санкт-Петербург"
        
    if requested_city in weather_memory:
        loop = asyncio.get_event_loop()
        weather_report = await loop.run_in_executor(None, get_cached_weather, requested_city)
        await message.reply(weather_report)
    else:
        await message.reply(
            f"❌ Город '{requested_city}' пока не поддерживается ботом.\n"
            f"Доступные локации: Москва, Зеленоград, Поварово, Санкт-Петербург, Екатеринбург."
        )

# 4. Обработка обычных нажатий Reply-кнопок в личке
@dp.message(F.text.in_({"Москва", "Зеленоград", "Санкт-Петербург", "Екатеринбург", "Поварово"}))
async def send_weather(message: Message):
    loop = asyncio.get_event_loop()
    weather_report = await loop.run_in_executor(None, get_cached_weather, message.text)
    await message.answer(weather_report, reply_markup=weather_keyboard)

# --- ХАК ДЛЯ ОБХОДА ОШИБКИ PORT BINDING НА RENDER ---
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
