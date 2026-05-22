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

    # Создаем веб-сервер
    app = web.Application()
    
    # Маршруты API
    app.router.add_get('/api/products', get_products_api)
    app.router.add_options('/api/products', options_handler)

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

    # Автоматически устанавливаем кнопку "Магазин 🌸" в левом нижнем углу чата Telegram
    from aiogram.types import MenuButtonWebApp, WebAppInfo
    try:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="Магазин 🌸",
                web_app=WebAppInfo(url=handlers.WEBAPP_URL)
            )
        )
        print("✅ Кнопка меню WebApp успешно установлена!")
    except Exception as e:
        print("⚠️ Не удалось установить кнопку меню WebApp:", e)

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