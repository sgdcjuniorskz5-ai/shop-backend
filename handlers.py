import json
from aiogram import types, F
from aiogram.filters import Command
from config import ADMIN_ID, WEBAPP_URL
from database import add_product, delete_product, get_all_products, get_product_by_id

ALLOWED_IMAGE_FORMATS = ['png', 'jpg', 'jpeg']

def validate_image_url(url):
    """Проверяет, что URL указывает на png или jpeg изображение"""
    if not url:
        return False
    url_lower = url.lower()
    return any(url_lower.endswith(f'.{fmt}') for fmt in ALLOWED_IMAGE_FORMATS)

async def start_handler(message: types.Message):
    kb = [[types.InlineKeyboardButton(text="Открыть магазин 🌸", web_app=types.WebAppInfo(url=WEBAPP_URL))]]
    markup = types.InlineKeyboardMarkup(inline_keyboard=kb)
    await message.answer(f"Привет, {message.from_user.first_name}! Выбирай цветы:", reply_markup=markup)

async def list_products_handler(message: types.Message):
    """Показывает список всех товаров текстом"""
    products = get_all_products()
    
    if not products:
        await message.answer("📭 К сожалению, магазин пуст. Свяжитесь с администратором.")
        return
    
    text = "📋 **Список доступных товаров:**\n\n"
    for product in products:
        prod_id = product[0]
        name = product[1]
        price = product[2]
        description = product[3] if len(product) > 3 else "Описание отсутствует"
        image_url = product[4] if len(product) > 4 else ""
        text += f"#{prod_id}️⃣ {name}\n💰 {price} ₸\n📝 {description}\n"
        if image_url:
            text += f"🖼 [Фото]({image_url})\n"
        text += "\n"
    
    kb = [[types.InlineKeyboardButton(text="Открыть магазин 🛍", web_app=types.WebAppInfo(url=WEBAPP_URL))]]
    markup = types.InlineKeyboardMarkup(inline_keyboard=kb)
    await message.answer(text, reply_markup=markup, parse_mode="Markdown")

async def web_app_data_handler(message: types.Message):
    """Обработка данных с веб-приложения"""
    try:
        data = json.loads(message.web_app_data.data)
        
        # Проверка наличия всех необходимых полей (чека)
        required_fields = ['item', 'quantity', 'price', 'product_id']
        if not all(field in data for field in required_fields):
            error_text = (
                "❌ **Ошибка оформления заказа!**\n\n"
                "Некорректные данные. Попробуйте еще раз.\n\n"
                "Возвращаемся в магазин..."
            )
            await message.answer(error_text, parse_mode="Markdown")
            
            # Предложение вернуться в магазин
            kb = [[types.InlineKeyboardButton(text="Вернуться в магазин 🌸", web_app=types.WebAppInfo(url=WEBAPP_URL))]]
            markup = types.InlineKeyboardMarkup(inline_keyboard=kb)
            await message.answer("Попробуйте еще раз:", reply_markup=markup)
            return
        
        # Проверка количества и цены
        try:
            qty = int(data['quantity'])
            price = float(data['price'])
            
            if qty <= 0 or price <= 0:
                raise ValueError("Неверные значения")
        except (ValueError, TypeError):
            error_text = (
                "❌ **Некорректное количество или цена!**\n"
                "Попробуйте еще раз."
            )
            await message.answer(error_text, parse_mode="Markdown")
            
            kb = [[types.InlineKeyboardButton(text="Вернуться в магазин 🌸", web_app=types.WebAppInfo(url=WEBAPP_URL))]]
            markup = types.InlineKeyboardMarkup(inline_keyboard=kb)
            await message.answer("Попробуйте еще раз:", reply_markup=markup)
            return
        
        # Успешный заказ
        text = (
            f"✅ **Заказ сформирован!**\n\n"
            f"🌸 Товар: {data['item']}\n"
            f"🔢 Количество: {qty} шт.\n"
            f"💰 Итого: {price} ₸\n"
            "────────────────────\n"
            "📱 Переведите на Kaspi:\n"
            "`+77XXXXXXXXX`\n\n"
            "После оплаты отправьте скриншот чека."
        )
        await message.answer(text, parse_mode="Markdown")
    
    except json.JSONDecodeError:
        await message.answer("❌ Ошибка обработки данных. Попробуйте еще раз.")
        
        kb = [[types.InlineKeyboardButton(text="Вернуться в магазин 🌸", web_app=types.WebAppInfo(url=WEBAPP_URL))]]
        markup = types.InlineKeyboardMarkup(inline_keyboard=kb)
        await message.answer("Попробуйте еще раз:", reply_markup=markup)

async def admin_add_product(message: types.Message):
    """Добавление товара администратором"""
    if message.from_user.id == ADMIN_ID:
        try:
            parts = message.text.split(maxsplit=4)
            if len(parts) < 5:
                await message.answer(
                    "❌ Ошибка! Неверное количество параметров.\n\n"
                    "Формат: `/add Название Цена Описание URL_изображения`\n\n"
                    "Пример: `/add Розы 1200 Красивые розы http://example.com/rose.png`\n\n"
                    "⚠️ Изображение должно быть в формате PNG или JPEG",
                    parse_mode="Markdown"
                )
                return
            
            name = parts[1]
            price = float(parts[2])
            description = parts[3]
            image_url = parts[4]
            
            # Валидация формата изображения
            if not validate_image_url(image_url):
                await message.answer(
                    "❌ Ошибка! Изображение должно быть в формате **PNG** или **JPEG**\n\n"
                    f"Вы указали: `{image_url}`\n\n"
                    "Допустимые форматы: `.png`, `.jpg`, `.jpeg`",
                    parse_mode="Markdown"
                )
                return
            
            add_product(name, price, description, image_url)
            await message.answer(f"✅ Товар '{name}' добавлен с изображением!")
        except ValueError:
            await message.answer("❌ Ошибка! Цена должна быть числом (например, 1200)", parse_mode="Markdown")
        except Exception as e:
            await message.answer(f"❌ Неизвестная ошибка: {str(e)}", parse_mode="Markdown")
    else:
        await message.answer("⛔ Доступ запрещен")

async def admin_delete_product(message: types.Message):
    """Удаление товара по ID"""
    if message.from_user.id == ADMIN_ID:
        try:
            p_id = int(message.text.split()[1])
            product = get_product_by_id(p_id)
            
            if not product:
                await message.answer(f"❌ Товар #{p_id} не найден!")
                return
                
            delete_product(p_id)
            await message.answer(f"🗑 Товар #{p_id} ({product[1]}) удален!")
        except (ValueError, IndexError):
            await message.answer("❌ Формат: `/del ID_товара`", parse_mode="Markdown")
    else:
        await message.answer("⛔ Доступ запрещен")