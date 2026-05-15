import json
from aiogram import types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import ADMIN_ID, WEBAPP_URL as CONFIG_WEBAPP_URL
from database import add_product, delete_product, get_all_products, get_product_by_id

WEBAPP_URL = CONFIG_WEBAPP_URL
LOCAL_WEB_URL = None

def set_webapp_url(url: str):
    global WEBAPP_URL
    WEBAPP_URL = url


def set_local_url(url: str):
    global LOCAL_WEB_URL
    LOCAL_WEB_URL = url


def build_shop_button(text: str):
    if WEBAPP_URL.startswith('https://'):
        return types.InlineKeyboardButton(text=text, web_app=types.WebAppInfo(url=WEBAPP_URL))
    return None

ALLOWED_IMAGE_FORMATS = ['png', 'jpg', 'jpeg']

class AddProductStates(StatesGroup):
    name = State()
    price = State()
    description = State()
    photo = State()


def validate_image_url(url):
    """Проверяет, что URL указывает на png или jpeg изображение"""
    if not url:
        return False
    url_lower = url.lower()
    return any(url_lower.endswith(f'.{fmt}') for fmt in ALLOWED_IMAGE_FORMATS)

async def start_handler(message: types.Message):
    description = f"Привет, {message.from_user.first_name}! Выбирай цветы:"
    button = build_shop_button("Открыть магазин 🌸")

    if button:
        markup = types.InlineKeyboardMarkup(inline_keyboard=[[button]])
        if LOCAL_WEB_URL:
            description += f"\n\nЛокальный магазин: [открыть]({LOCAL_WEB_URL})"
        await message.answer(description, reply_markup=markup, parse_mode="Markdown")
    else:
        description += f"\n\n🔗 [Открыть магазин]({WEBAPP_URL})"
        if LOCAL_WEB_URL:
            description += f"\nЛокальный магазин: [открыть]({LOCAL_WEB_URL})"
        await message.answer(description, parse_mode="Markdown")

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
    
    button = build_shop_button("Открыть магазин 🛍")
    if button:
        markup = types.InlineKeyboardMarkup(inline_keyboard=[[button]])
        if LOCAL_WEB_URL:
            text += f"\nЛокальный магазин: [открыть]({LOCAL_WEB_URL})"
        await message.answer(text, reply_markup=markup, parse_mode="Markdown")
    else:
        text += f"🔗 [Открыть магазин]({WEBAPP_URL})\n\n"
        if LOCAL_WEB_URL:
            text += f"Локальный магазин: [открыть]({LOCAL_WEB_URL})\n\n"
        text += "⚠️ Локальный магазин работает через обычную ссылку. Откроется в браузере."
        await message.answer(text, parse_mode="Markdown")

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

async def admin_add_product(message: types.Message, state: FSMContext):
    """Запуск интерактивного добавления товара"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Доступ запрещен")
        return

    await state.set_state(AddProductStates.name)
    await message.answer(
        "Введите название товара:",
        parse_mode="Markdown"
    )


async def add_product_name(message: types.Message, state: FSMContext):
    name = message.text and message.text.strip()
    if not name:
        await message.answer("❌ Название не может быть пустым. Введите название товара:")
        return

    await state.update_data(name=name)
    await state.set_state(AddProductStates.price)
    await message.answer("Введите цену товара в тенге за штуку:")


async def add_product_price(message: types.Message, state: FSMContext):
    try:
        price = float(message.text.replace(',', '.').strip())
        if price <= 0:
            raise ValueError()
    except Exception:
        await message.answer("❌ Неверная цена. Введите число в тенге за штуку, например 1200:")
        return

    await state.update_data(price=price)
    await state.set_state(AddProductStates.description)
    await message.answer("Введите описание товара:")


async def add_product_description(message: types.Message, state: FSMContext):
    description = message.text and message.text.strip()
    if not description:
        await message.answer("❌ Описание не может быть пустым. Введите описание товара:")
        return

    await state.update_data(description=description)
    await state.set_state(AddProductStates.photo)
    await message.answer(
        "Прикрепите фото товара или отправьте ссылку на изображение.\n"
        "Если фото не требуется, напишите: пропустить",
        parse_mode="Markdown"
    )


async def add_product_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    image_url = None

    if message.photo:
        file = await message.bot.get_file(message.photo[-1].file_id)
        image_url = f"https://api.telegram.org/file/bot{message.bot.token}/{file.file_path}"
    elif message.text:
        text = message.text.strip()
        if text.lower() in ('пропустить', 'skip'):
            image_url = 'https://via.placeholder.com/150/fce4ec/880e4f'
        elif validate_image_url(text):
            image_url = text
        else:
            await message.answer(
                "❌ Некорректная ссылка на изображение. Отправьте URL с расширением .png/.jpg/.jpeg или напишите 'пропустить'."
            )
            return
    else:
        await message.answer(
            "❌ Пожалуйста, прикрепите фото или отправьте ссылку на изображение, либо напишите 'пропустить'."
        )
        return

    add_product(data['name'], data['price'], data['description'], image_url)
    await state.clear()
    await message.answer(f"✅ Товар '{data['name']}' добавлен в магазин!")

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