import asyncio
import json
import os
import re
import shutil
import sys
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from config import API_TOKEN, ADMIN_ID, KASPI_NUMBER
import handlers
from database import init_db, get_all_products


def update_env_file(env_path: str, key: str, value: str) -> bool:
    try:
        lines = []
        found = False

        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip().startswith(f"{key}="):
                        lines.append(f"{key}={value}\n")
                        found = True
                    else:
                        lines.append(line)

        if not found:
            lines.append(f"{key}={value}\n")

        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        return True
    except Exception as e:
        print('⚠️ Ошибка записи .env:', e)
        return False


async def start_cloudflared_tunnel(local_port: int, env_path: str | None = None):
    cloudflared_cmd = shutil.which('cloudflared') or shutil.which('cloudflared.exe')
    if not cloudflared_cmd:
        print('⚠️ cloudflared не найден в PATH. Пропускаю запуск Cloudflare Tunnel.')
        if 'PATH' in os.environ:
            print('PATH:', os.environ['PATH'])
        return None, None

    try:
        proc = await asyncio.create_subprocess_exec(
            cloudflared_cmd,
            'tunnel',
            '--url',
            f'http://localhost:{local_port}',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
    except Exception as e:
        print('⚠️ Ошибка запуска cloudflared:', e)
        return None, None

    public_url = None
    start_time = asyncio.get_event_loop().time()
    timeout = 15.0

    while True:
        line = await proc.stdout.readline()
        if not line:
            break

        decoded = line.decode('utf-8', errors='ignore').strip()
        print(f'cloudflared: {decoded}')

        match = re.search(r'https://[^\s"\']+\.trycloudflare\.com', decoded)
        if match:
            public_url = match.group(0)
            break

        if asyncio.get_event_loop().time() - start_time > timeout:
            break

    if public_url:
        print(f'✅ Cloudflare Tunnel запущен: {public_url}')
        if env_path:
            update_env_file(env_path, 'WEBAPP_URL', public_url)
        return proc, public_url

    print('⚠️ Не удалось получить публичный URL из cloudflared за время ожидания.')
    return proc, None


async def main():
    init_db()
    bot = Bot(token=API_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрируем обработчики
    dp.message.register(handlers.start_handler, Command("start"))
    dp.message.register(handlers.list_products_handler, Command("list"))
    dp.message.register(handlers.admin_add_product, Command("add"))
    dp.message.register(handlers.add_product_name, handlers.AddProductStates.name)
    dp.message.register(handlers.add_product_price, handlers.AddProductStates.price)
    dp.message.register(handlers.add_product_description, handlers.AddProductStates.description)
    dp.message.register(handlers.add_product_photo, handlers.AddProductStates.photo)
    dp.message.register(handlers.admin_delete_product, Command("del"))
    dp.message.register(handlers.admin_discount, Command("discount"))
    dp.message.register(handlers.admin_del_discount, Command("deldiscount"))
    dp.message.register(handlers.web_app_data_handler, F.content_type == "web_app_data")
    # Регистрация обработчика для получения чека (фото/документ)
    dp.message.register(handlers.receipt_handler, F.photo | F.document)

    # API для получения товаров с CORS
    async def get_products_api(request):
        products = get_all_products()
        product_list = [
            {
                "id": p[0],
                "name": p[1],
                "price": p[2],
                "description": p[3] if len(p) > 3 else "Описание отсутствует",
                "image_url": p[4] if len(p) > 4 else "https://via.placeholder.com/150/fce4ec/880e4f",
                "discount": p[5] if len(p) > 5 else 0,
                "discounted_price": round(p[2] * (100 - (p[5] if len(p) > 5 else 0)) / 100) if (p[5] if len(p) > 5 else 0) > 0 else None
            }
            for p in products
        ]
        resp = web.json_response(product_list)
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return resp

    # Обработчик OPTIONS для CORS
    async def options_handler(request):
        resp = web.Response()
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return resp

    # Приём заказов из веба и отправка сообщения напрямую в чат
    async def post_order_api(request):
        try:
            data = await request.json()
        except Exception:
            return web.json_response({'error': 'Invalid JSON'}, status=400)

        required = ['product_id', 'item', 'quantity', 'price', 'name', 'address']
        if not all(k in data for k in required):
            return web.json_response({'error': 'Missing fields'}, status=400)

        import random, string, time
        def gen_code(n=8):
            return ''.join(random.choices(string.ascii_uppercase + string.digits, k=n))

        order_code = gen_code(8)
        user_id = data.get('user_id')
        order_record = {
            'product_id': data.get('product_id'),
            'item': data.get('item'),
            'quantity': data.get('quantity'),
            'price': data.get('price'),
            'name': data.get('name'),
            'address': data.get('address'),
            'user_contact': str(user_id) if user_id else None,
            'created_at': time.time()
        }
        
        try:
            handlers.add_pending_order(order_code, order_record)
        except Exception as e:
            print('Failed to store pending order:', e)

        sent_to_chat = False
        if user_id:
            bot = request.app['bot']
            text = (
                f"✅ **Заказ `{order_code}` сформирован!**\n\n"
                f"🌸 Товар: {data['item']}\n"
                f"🔢 Количество: {data['quantity']} шт.\n"
                f"💰 Итого: {data['price']} ₸\n"
                f"👤 Имя: {data['name']}\n"
                f"📍 Адрес: {data['address']}\n\n"
                "────────────────────\n"
                "💳 **Оплата через Kaspi:**\n\n"
                f"1️⃣ Переведите **{data['price']} ₸** на Kaspi:\n"
                f"`{KASPI_NUMBER}`\n\n"
                "2️⃣ В комментарии к переводу укажите:\n"
                f"`{order_code}`\n\n"
                "3️⃣ Отправьте скриншот чека в этот чат"
            )
            try:
                await bot.send_message(user_id, text, parse_mode="Markdown")
                sent_to_chat = True
            except Exception as e:
                print(f"Failed to send direct message to user {user_id}: {e}")

        # Уведомление админа о новом заказе
        admin_text = (
            f"🆕 **Новый заказ `{order_code}`**\n\n"
            f"🌸 Товар: {data['item']}\n"
            f"🔢 Количество: {data['quantity']} шт.\n"
            f"💰 Сумма: {data['price']} ₸\n"
            f"👤 Имя: {data['name']}\n"
            f"📍 Адрес: {data['address']}\n"
            f"🆔 Пользователь: {f'id={user_id}' if user_id else 'не определён'}\n\n"
            "⏳ **Статус: Ожидает оплату**"
        )
        try:
            bot = request.app['bot']
            await bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown")
        except Exception as e:
            print(f"Failed to notify admin about new order: {e}")

        resp = web.json_response({
            'status': 'ok',
            'order_code': order_code,
            'kaspi_number': KASPI_NUMBER,
            'total': data.get('price'),
            'sent_to_chat': sent_to_chat,
            'item': data.get('item'),
            'quantity': data.get('quantity')
        })
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return resp

    # Создаем веб-сервер
    app = web.Application()
    app['bot'] = bot
    
    # Маршруты API
    app.router.add_get('/api/products', get_products_api)
    app.router.add_options('/api/products', options_handler)
    app.router.add_post('/api/order', post_order_api)
    app.router.add_options('/api/order', options_handler)

    # Локальный веб-магазин
    web_dir = os.path.dirname(os.path.abspath(__file__))
    app.router.add_get('/', lambda request: web.FileResponse(os.path.join(web_dir, 'index.html')))
    app.router.add_static('/static', web_dir, show_index=False)

    # Запускаем веб-сервер с подбором свободного порта
    runner = web.AppRunner(app)
    await runner.setup()

    preferred_port = int(os.getenv('PORT', '8080'))
    candidate_ports = [preferred_port, 8081, 8082]
    selected_port = None
    site = None

    for port in candidate_ports:
        try:
            site = web.TCPSite(runner, '0.0.0.0', port)
            await site.start()
            selected_port = port
            break
        except OSError as e:
            if e.errno == 10048 or 'address already in use' in str(e).lower():
                print(f"⚠️ Порт {port} занят, пробую другой порт...")
                continue
            raise

    if selected_port is None:
        raise RuntimeError('Не удалось запустить веб-сервер: все порты заняты.')

    local_url = f'http://localhost:{selected_port}/'
    handlers.set_local_url(local_url)

    env_path = os.path.join(web_dir, '.env')
    cloudflared_proc, cloudflared_url = await start_cloudflared_tunnel(selected_port, env_path)
    if cloudflared_url:
        handlers.set_webapp_url(cloudflared_url)
        print(f"🌐 WebApp URL установлен через Cloudflare Tunnel: {cloudflared_url}")
    else:
        print("🌐 Используется WEBAPP_URL из config.py или .env.")

    print("✅ Бот запущен!")
    print(f"📱 API: http://localhost:{selected_port}/api/products")
    print(f"🌐 Локальный веб-магазин: {local_url}")
    
    # Запускаем polling бота
    try:
        await dp.start_polling(bot)
    finally:
        if cloudflared_proc is not None:
            cloudflared_proc.terminate()
            try:
                await asyncio.wait_for(cloudflared_proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                cloudflared_proc.kill()
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())