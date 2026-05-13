import json
from aiogram import types, F
from aiogram.filters import Command
from config import ADMIN_ID, WEBAPP_URL
from database import add_product, delete_product

async def start_handler(message: types.Message):
    kb = [[types.InlineKeyboardButton(text="Открыть магазин 🌸", web_app=types.WebAppInfo(url=WEBAPP_URL))]]
    markup = types.InlineKeyboardMarkup(inline_keyboard=kb)
    await message.answer(f"Привет, {message.from_user.first_name}! Выбирай цветы:", reply_markup=markup)

async def web_app_data_handler(message: types.Message):
    data = json.loads(message.web_app_data.data)
    text = (
        f"🛍 **Заказ сформирован!**\n\n"
        f"🌸 Товар: {data['item']}\n"
        f"🔢 Количество: {data['quantity']} шт.\n"
        f"💰 Итого: {data['price']} ₸\n"
        "────────────────────\n"
        "Переведите на Kaspi: `+77XXXXXXXXX`"
    )
    await message.answer(text, parse_mode="Markdown")

async def admin_add_product(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        try:
            parts = message.text.split(maxsplit=3)
            add_product(parts[1], float(parts[2]), parts[3])
            await message.answer("✅ Товар добавлен!")
        except:
            await message.answer("Ошибка! Формат: /add Название Цена Описание")

async def admin_delete_product(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        try:
            p_id = int(message.text.split()[1])
            delete_product(p_id)
            await message.answer(f"🗑 Товар #{p_id} удален!")
        except:
            await message.answer("Формат: /del ID_товара")