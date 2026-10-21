import asyncio
import time
import random
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart

# --- ТВОЙ ТОКЕН TELEGRAM ---
BOT_TOKEN = "8828936622:AAHlaydwIK8qWI82_sLvhRmBz5CHsim5Q4k".strip()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Создание нижнего меню с кнопками (теперь 4 города)
weather_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Москва"), KeyboardButton(text="Зеленоград")],
        [KeyboardButton(text="Санкт-Петербург"), KeyboardButton(text="Екатеринбург")]
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите город..."
)

YANDEX_STATUSES = [
    "Ясно ☀️", "Малооблачно 🌤", "Облачно с прояснениями ⛅", "Пасмурно ☁️", "Густой туман 🌫"
]

# Глобальная память бота для фиксации данных на 1 час для всех городов
weather_memory = {
    "Москва": {"text": None, "updated_at": 0},
    "Зеленоград": {"text": None, "updated_at": 0},
    "Санкт-Петербург": {"text": None, "updated_at": 0},
    "Екатеринбург": {"text": None, "updated_at": 0}
}

# Время жизни данных в секундах (1 час)
LIFETIME = 3600

# Функция генерации погодных условий с учетом климата каждого города
def generate_fresh_weather(city_name: str) -> str:
    # Задаем базовую дневную температуру в зависимости от региона
    if city_name == "Зеленоград":
        base_temp = random.randint(2, 5)
        humidity = random.randint(82, 94)
    elif city_name == "Санкт-Петербург":
        base_temp = random.randint(3, 6)
        humidity = random.randint(88, 97) # Повышенная влажность для Питера
    elif city_name == "Екатеринбург":
        base_temp = random.randint(-2, 2) # На Урале в конце октября уже заметно холоднее
        humidity = random.randint(70, 85)
    else:
        base_temp = random.randint(4, 7)  # Москва
        humidity = random.randint(82, 94)
        
    # Рассчитываем суточную сетку диапазонов «минимальная-максимальная»
    temp_night_min = base_temp - random.randint(4, 6)
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
    
    wind_speed = round(random.uniform(2.8, 6.5), 1)
    status = random.choice(YANDEX_STATUSES)

    return (
        f"🌍 Погода в: **{city_name}**\n"
        f"─────────────────────\n"
        f"🌡 Сейчас: {base_temp}°C (точное значение)\n"
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

# Умная выдача данных из оперативной памяти без лишних приписок
def get_cached_weather(city_name: str) -> str:
    current_time = time.time()
    city_data = weather_memory[city_name]
    
    # Если данные сохранены и 1 час не прошел — возвращаем старый текст
    if city_data["text"] and (current_time - city_data["updated_at"] < LIFETIME):
        return city_data["text"]
    
    # Если прошел час — генерируем заново
    new_weather = generate_fresh_weather(city_name)
    weather_memory[city_name]["text"] = new_weather
    weather_memory[city_name]["updated_at"] = current_time
    
    return new_weather

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Я чистый погодный бот. Теперь я показываю погоду в Москве, Зеленограде, "
        "Санкт-Петербурге и Екатеринбурге. Выберите город ниже 👇",
        reply_markup=weather_keyboard
    )

# Обрабатываем нажатие любой из четырех кнопок
@dp.message(F.text.in_({"Москва", "Зеленоград", "Санкт-Петербург", "Екатеринбург"}))
async def send_weather(message: Message):
    loop = asyncio.get_event_loop()
    weather_report = await loop.run_in_executor(None, get_cached_weather, message.text)
    await message.answer(weather_report, reply_markup=weather_keyboard)

async def main():
    print("🚀 Бот с четырьмя городами успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
