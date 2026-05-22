import json
from aiogram import types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import ADMIN_ID, WEBAPP_URL as CONFIG_WEBAPP_URL, KASPI_NUMBER
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


# Pending orders storage for orders created outside WebApp
# key: order_code -> dict with order data and timestamp
pending_orders = {}

def add_pending_order(code: str, order: dict):
    pending_orders[code] = {**order, 'created_at': __import__('time').time()}

def pop_pending_order_by_code(code: str):
    return pending_orders.pop(code, None)

def find_pending_order_for_user(user_id: int, username: str | None = None):
    # Try to find by numeric chat_id stored in user_contact, or by username match
    for code, o in list(pending_orders.items()):
        uc = o.get('user_contact')
        try:
            if uc is not None and int(str(uc)) == user_id:
                return code, o
        except Exception:
            pass
        if username and uc:
            if isinstance(uc, str) and uc.lstrip('@').lower() == username.lower():
                return code, o
    return None, None


async def start_handler(message: types.Message):
    description = f"Привет, {message.from_user.first_name}! Добро пожаловать в цветочный магазин, нажми на кнопку чтобы открыть магазин"
    
    # Создаем ReplyKeyboardMarkup (обычную кнопку под вводом текста).
    # Она на 100% поддерживает tg.sendData() в Telegram.
    keyboard = [
        [types.KeyboardButton(text="Открыть магазин 🌸", web_app=types.WebAppInfo(url=WEBAPP_URL))]
    ]
    markup = types.ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

    await message.answer(description, reply_markup=markup, parse_mode="Markdown")

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
    
    # Отправляем обычную клавиатуру как в старт хендлере
    keyboard = [
        [types.KeyboardButton(text="Открыть магазин 🛍", web_app=types.WebAppInfo(url=WEBAPP_URL))]
    ]
    markup = types.ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
    await message.answer(text, reply_markup=markup, parse_mode="Markdown")

async def web_app_data_handler(message: types.Message):
    """Обработка данных с веб-приложения"""
    print(f"DEBUG: Получены данные от WebApp: {message.web_app_data.data}")
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
        import random, string

        def gen_code(n=8):
            return ''.join(random.choices(string.ascii_uppercase + string.digits, k=n))

        order_code = gen_code(8)
        customer_name = data.get('name', 'Не указано')
        customer_address = data.get('address', 'Не указан')

        # Сохраняем pending order для сопоставления чека
        order_data = {
            'product_id': data.get('product_id'),
            'item': data['item'],
            'quantity': qty,
            'price': price,
            'name': customer_name,
            'address': customer_address,
            'user_contact': str(message.from_user.id),
        }
        add_pending_order(order_code, order_data)

        text = (
            f"✅ **Заказ `{order_code}` сформирован!**\n\n"
            f"🌸 Товар: {data['item']}\n"
            f"🔢 Количество: {qty} шт.\n"
            f"💰 Итого: {price} ₸\n"
            f"👤 Имя: {customer_name}\n"
            f"📍 Адрес: {customer_address}\n\n"
            "────────────────────\n"
            "💳 **Оплата через Kaspi:**\n\n"
            f"1️⃣ Переведите **{price} ₸** на Kaspi:\n"
            f"`{KASPI_NUMBER}`\n\n"
            "2️⃣ В комментарии к переводу укажите:\n"
            f"`{order_code}`\n\n"
            "3️⃣ Отправьте скриншот чека в этот чат"
        )
        await message.answer(text, parse_mode="Markdown")
    
    except json.JSONDecodeError:
        await message.answer("❌ Ошибка обработки данных. Попробуйте еще раз.")
        
        kb = [[types.InlineKeyboardButton(text="Вернуться в магазин 🌸", web_app=types.WebAppInfo(url=WEBAPP_URL))]]
        markup = types.InlineKeyboardMarkup(inline_keyboard=kb)
        await message.answer("Попробуйте еще раз:", reply_markup=markup)


async def receipt_handler(message: types.Message):
    """Обработка фото/документа с чеком от пользователя. Ищем код заказа в подписи или сопоставляем по user_id/username."""
    # get caption (for document) or caption for photo
    caption = getattr(message, 'caption', None) or ''

    # Try to find order code in caption (simple alphanumeric token)
    import re as _re
    match = _re.search(r'([A-Za-z0-9\-]{6,})', caption or '')
    matched_code = match.group(1) if match else None

    order = None
    order_code = None
    if matched_code:
        order = pop_pending_order_by_code(matched_code)
        order_code = matched_code if order else None

    if not order:
        # Try to find by user id or username
        code, o = find_pending_order_for_user(message.from_user.id, getattr(message.from_user, 'username', None))
        if code:
            order = pop_pending_order_by_code(code)
            order_code = code

    if not order:
        await message.answer('⚠️ Не найден соответствующий ожидающий заказ. Пожалуйста, отправьте чек с кодом заказа в подписи.')
        return

    # Forward the receipt (the message) to admin and send order details
    customer_name = order.get('name', 'Не указано')
    customer_address = order.get('address', 'Не указан')
    
    admin_text = (
        f"📦 Получен чек к заказу {order_code or ''}\n\n"
        f"Товар: {order.get('item')}\n"
        f"Количество: {order.get('quantity')}\n"
        f"Сумма: {order.get('price')} ₸\n"
        f"👤 Имя: {customer_name}\n"
        f"📍 Адрес: {customer_address}\n"
        f"Отправитель: @{getattr(message.from_user, 'username', '')} (id={message.from_user.id})\n"
    )

    try:
        await message.bot.send_message(ADMIN_ID, admin_text)
        # forward the actual media message to admin
        await message.forward(ADMIN_ID)
    except Exception as e:
        print('Failed to forward receipt to admin:', e)
        await message.answer('⚠️ Не удалось отправить чек администратору. Попробуйте позже.')
        return

    await message.answer('✅ Спасибо! Чек получен и отправлен продавцу. Ожидайте подтверждения.')

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