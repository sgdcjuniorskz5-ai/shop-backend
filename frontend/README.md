Frontend for Цветочная Лавка

Instructions:

1) Set `meta` API base in `index.html` before deploying to GitHub Pages if backend is hosted elsewhere (Render):

```html
<meta name="api-base" content="https://<your-backend>.onrender.com/api">
```

2) Deploy to GitHub Pages (branch `main` / folder `/`). After deployment, set `WEBAPP_URL` in backend to the Pages URL.

3) If you need to update products, use the Telegram bot commands `/add` and `/del` (no frontend changes required for product data updates).
