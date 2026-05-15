Шаги деплоя на Render (быстрое руководство)

1) Подготовка репозитория

- Инициализируйте git и отправьте текущую папку в GitHub:

```bash
git init
git add .
git commit -m "Prepare app for Render"
git branch -M main
git remote add origin git@github.com:<your>/<repo>.git
git push -u origin main
```

2) Подготовка фронтенда (GitHub Pages)

- В отдельный репозиторий (например, `<your>/shop-frontend`) поместите `index.html`, `script.js`, `style.css`.
- Включите GitHub Pages (ветка `main` / папка `/` или `/docs`). URL будет `https://<your>.github.io/<repo>`.

3) Создание Web Service на Render

- Перейдите в https://render.com и создайте новый Web Service.
- Подключите репозиторий с бэкендом (тот, где `main.py`).
- Build Command: оставьте пустым или `pip install -r requirements.txt`.
- Start Command: `python main.py` (или оставьте пустым, Render прочитает `Procfile`).
- Environment Variables:
  - `BOT_TOKEN` — ваш токен бота
  - `ADMIN_ID` — ваш Telegram ID администратора
  - `WEBAPP_URL` — URL фронтенда на GitHub Pages (например, `https://<your>.github.io/<repo>`)

  Дополнительно: если фронтенд размещается отдельно (на GitHub Pages), укажите в `index.html` мета-тег `api-base` с URL вашего backend (Render), например:

  ```html
  <meta name="api-base" content="https://<your-backend>.onrender.com/api">
  ```

  Это нужно, чтобы фронтенд на GitHub Pages знал, куда отправлять запросы к `/api/products` и `/api/order`.

4) База данных и хранение

- В текущей реализации используется SQLite `shop.db` в рабочей директории. Render Web Services предоставляют постоянный диск для приложения, но для надёжности рекомендуется использовать внешнюю БД (Postgres) при росте.

5) Тестирование

- После деплоя проверьте логи Render и откройте `https://<render-service>.onrender.com/api/products` — должны вернуться товары в JSON.
- Убедитесь, что `WEBAPP_URL` указывает на публичный frontend — бот будет формировать кнопку с этим URL.

6) Обновление товаров

- Управляйте товарами через команды бота `/add` и `/del` — это не требует деплоя.

Если хотите, могу автоматически подготовить и запушить фронтенд в новый репозиторий (A: сделать это сейчас). Также могу подготовить пример `docker`-файла, если предпочтете Docker deploy.
