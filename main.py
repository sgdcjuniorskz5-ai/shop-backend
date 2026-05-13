import asyncio
import json
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from config import API_TOKEN
import handlers
from database import init_db, get_all_products

async def main():
    init_db()
    bot = Bot(token=API_TOKEN)
    dp = Dispatcher()

    # Регистрируем обработчики
    dp.message.register(handlers.start_handler, Command("start"))
    dp.message.register(handlers.list_products_handler, Command("list"))
    dp.message.register(handlers.admin_add_product, Command("add"))
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

    # Создаем веб-сервер только для API
    app = web.Application()
    
    # Маршруты
    app.router.add_get('/api/products', get_products_api)
    app.router.add_options('/api/products', options_handler)

    # Запускаем веб-сервер на порту 8080
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()

    print("✅ Бот запущен!")
    print("📱 API: http://localhost:8080/api/products")
    print("🌐 Веб-магазин: https://sgdcjuniorskz5-ai.github.io/shop-bot/")
    
    # Запускаем polling бота
    try:
        await dp.start_polling(bot)
    finally:
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())