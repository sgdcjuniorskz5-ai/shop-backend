import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from config import API_TOKEN
import handlers
from database import init_db

async def main():
    init_db()
    bot = Bot(token=API_TOKEN)
    dp = Dispatcher()

    # Регистрируем обработчики
    dp.message.register(handlers.start_handler, Command("start"))
    dp.message.register(handlers.admin_add_product, Command("add"))
    dp.message.register(handlers.admin_delete_product, Command("del"))
    dp.message.register(handlers.web_app_data_handler, F.content_type == "web_app_data")

    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())