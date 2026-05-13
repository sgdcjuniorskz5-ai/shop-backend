import asyncio
import json
import os
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup

# Импортируем функции из нашего файла database.py
from database import init_db, add_product

# Загружаем настройки из .env
load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
WEBAPP_URL = os.getenv("WEBAPP_URL")

# Настройка логирования
logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- ОБРАБОТЧИКИ ---

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    """Отправляет кнопку открытия Mini App магазина"""
    kb = [
        [InlineKeyboardButton(
            text="Открыть магазин 🌸", 
            web_app=WebAppInfo(url=WEBAPP_URL)
        )]
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=kb)
    
    await message.answer(
        f"Здравствуйте, {message.from_user.first_name}! 🌷\n"
        "Добро пожаловать в цветочный бутик.\n"
        "Нажмите на кнопку ниже, чтобы выбрать идеальный букет:",
        reply_markup=markup
    )

@dp.message(Command("add"))
async def cmd_add(message: types.Message):
    """Админ-команда для добавления товара в БД"""
    if message.from_user.id != ADMIN_ID:
        return
    
    try:
        # Формат: /add Роза 1500 Красивое_описание
        parts = message.text.split(maxsplit=3)
        name, price, desc = parts[1], float(parts[2]), parts[3]
        
        add_product(name, price, desc, "no_photo")
        await message.answer(f"✅ Товар '{name}' добавлен!")
    except Exception:
        await message.answer("⚠️ Ошибка! Формат: /add Название Цена Описание")

@dp.message(F.content_type == types.ContentType.WEB_APP_DATA)
async def web_app_data_handler(message: types.Message):
    """Принимает данные о покупке из JS-кода магазина"""
    try:
        data = json.loads(message.web_app_data.data)
        item = data.get("item")
        price = data.get("price")
        
        # Сообщение клиенту
        await message.answer(
            f"🛍 **Заказ подтвержден!**\n\n"
            f"📦 Товар: {item}\n"
            f"💰 Сумма: {price} ₸\n"
            "────────────────────\n"
            "💳 **Оплата Kaspi:**\n"
            "Переведите на номер: `+77XXXXXXXXX` (Имя Г.)\n\n"
            "Пришлите скриншот чека в этот чат! ✨",
            parse_mode="Markdown"
        )
        
        # Уведомление админу
        await bot.send_message(
            ADMIN_ID, 
            f"🔔 **Новый заказ!**\nОт: @{message.from_user.username}\nТовар: {item}\nСумма: {price} ₸"
        )
    except Exception as e:
        logging.error(f"Web App Data Error: {e}")

async def main():
    init_db() # Создаем базу данных
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())