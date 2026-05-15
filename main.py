import asyncio
import json
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from config import API_TOKEN, ADMIN_ID
import handlers
from database import init_db, get_all_products

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
    dp.message.register(handlers.web_app_data_handler, F.content_type == "web_app_data")

    # API для получения товаров с CORS
    async def get_products_api(request):
        products = get_all_products()
        product_list = [
            {
                "id": p[0],
                "name": p[1],
                "price": p[2],
                "description": p[3] if len(p) > 3 else "Описание отсутствует",
                "image_url": p[4] if len(p) > 4 else "https://via.placeholder.com/150/fce4ec/880e4f"
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
        resp.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return resp

    # Приём заказов из веба (для случаев, когда WebApp недоступен)
    async def post_order_api(request):
        try:
            data = await request.json()
        except Exception:
            return web.json_response({'error': 'Invalid JSON'}, status=400)

        required = ['product_id', 'item', 'quantity', 'price']
        if not all(k in data for k in required):
            return web.json_response({'error': 'Missing fields'}, status=400)

        # Отправляем уведомление администратору через бота
        try:
            text = (
                f"📦 Новый заказ (вне Telegram WebApp)\n\n"
                f"Товар: {data.get('item')}\n"
                f"ID товара: {data.get('product_id')}\n"
                f"Количество: {data.get('quantity')}\n"
                f"Сумма: {data.get('price')} ₸\n\n"
                "(Пользователь открыл магазин вне WebApp — проверьте связь с клиентом.)"
            )
            await bot.send_message(ADMIN_ID, text)
        except Exception as e:
            print('Failed to send order to admin:', e)

        resp = web.json_response({'status': 'ok'})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return resp

    # Создаем веб-сервер
    app = web.Application()
    
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

    print("✅ Бот запущен!")
    print(f"📱 API: http://localhost:{selected_port}/api/products")
    print(f"🌐 Локальный веб-магазин: {local_url}")
    
    # Запускаем polling бота
    try:
        await dp.start_polling(bot)
    finally:
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())