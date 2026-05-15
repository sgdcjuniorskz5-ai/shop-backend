const tg = window.Telegram?.WebApp;
const isWebApp = !!tg;

if (tg) {
    tg.expand();
}

const productsContainer = document.querySelector('.products-grid');
const warningContainer = document.querySelector('.webapp-warning');
// Allow overriding API base via <meta name="api-base" content="https://your-backend.onrender.com/api">
const metaApi = document.querySelector('meta[name="api-base"]');
const API_BASE = metaApi && metaApi.content && metaApi.content.trim()
    ? metaApi.content.trim().replace(/\/$/, '')
    : (window.location.protocol === 'file:' ? 'http://localhost:8080/api' : `${window.location.origin}/api`);
const API_URL = `${API_BASE}/products`;

if (!isWebApp) {
    warningContainer.innerHTML = '<p style="text-align: center; color: #b00020; margin-bottom: 15px;">⚠️ Магазин открыт вне Telegram WebApp. Откройте бота в мобильном приложении Telegram и нажмите кнопку магазина в чате. Веб-версия браузера и внешние ссылки не работают для заказа.</p>';
}

if (window.location.protocol === 'file:') {
    productsContainer.innerHTML = '<p style="text-align: center; grid-column: 1/-1; color: red;">Откройте магазин через локальный сервер: <strong>http://localhost:8080/</strong></p>';
}

// Загружаем товары при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    loadProducts();
    const refreshBtn = document.getElementById('refresh-btn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', loadProducts);
    }
});

window.addEventListener('focus', loadProducts);

async function loadProducts() {
    try {
        const response = await fetch(API_URL);
        
        if (!response.ok) {
            throw new Error('Ошибка загрузки товаров');
        }
        
        const products = await response.json();
        
        if (products.length === 0) {
            productsContainer.innerHTML = '<p style="text-align: center; grid-column: 1/-1;">К сожалению, магазин пуст</p>';
            return;
        }
        
        // Очищаем контейнер и добавляем товары
        productsContainer.innerHTML = '';
        products.forEach(product => {
            const card = createProductCard(product);
            productsContainer.appendChild(card);
        });
        
    } catch (error) {
        console.error('Ошибка:', error);
        productsContainer.innerHTML = `<p style="text-align: center; grid-column: 1/-1; color: red;">Ошибка загрузки товаров: ${error.message}</p>`;
    }
}

function createProductCard(product) {
    const card = document.createElement('div');
    card.className = 'card';
    
    const qtyId = `qty-product-${product.id}`;
    
    card.innerHTML = `
        <img src="${product.image_url}" alt="${product.name}" onerror="this.src='https://via.placeholder.com/150/fce4ec/880e4f?text=no-image'">
        <div class="card-title">${product.name}</div>
        <div class="card-price">${product.price} ₸ / шт.</div>
        <div class="card-description">${product.description}</div>
        
        <div class="quantity-selector">
            <input type="number" id="${qtyId}" value="1" min="1">
            <div class="presets">
                <button onclick="setQty('${qtyId}', 1)">1</button>
                <button onclick="setQty('${qtyId}', 5)">5</button>
                <button onclick="setQty('${qtyId}', 25)">25</button>
                <button onclick="setQty('${qtyId}', 51)">51</button>
                <button onclick="setQty('${qtyId}', 101)">101</button>
            </div>
        </div>
        
        <button class="buy-btn" onclick="prepareOrder('${product.name}', ${product.price}, '${qtyId}', ${product.id})">Купить</button>
    `;
    
    return card;
}

function setQty(id, value) {
    document.getElementById(id).value = value;
}

async function prepareOrder(name, pricePerOne, qtyId, productId) {
    const qtyElement = document.getElementById(qtyId);
    const qty = parseInt(qtyElement.value);
    
    // Проверка корректности количества
    if (isNaN(qty) || qty <= 0) {
        alert('❌ Пожалуйста, укажите корректное количество!');
        return;
    }
    
    const totalPrice = pricePerOne * qty;
    
    const data = {
        product_id: productId,
        item: name,
        quantity: qty,
        price: totalPrice
    };

    if (!isWebApp) {
        const fallbackText = `Заказ не может быть отправлен автоматически вне Telegram.\n\nТовар: ${name}\nКоличество: ${qty}\nСумма: ${totalPrice} ₸\nID товара: ${productId}\n\nОткройте магазин через Telegram и повторите заказ.`;
        copyText(fallbackText);

        // Попытка отправить заказ на сервер (чтобы админ получил уведомление)
        try {
            const res = await fetch(`${API_BASE}/order`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            if (res.ok) {
                alert('⚠️ Магазин открыт вне Telegram. Текст заказа скопирован, и уведомление отправлено администратору.');
            } else {
                alert('⚠️ Магазин открыт вне Telegram. Текст заказа скопирован. Не удалось отправить уведомление администратору.');
            }
        } catch (err) {
            console.warn('Order POST failed', err);
            alert('⚠️ Магазин открыт вне Telegram. Текст заказа скопирован. Не удалось отправить уведомление администратору.');
        }
        return;
    }

    tg.sendData(JSON.stringify(data));
}

function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).catch(() => {
            console.warn('Не удалось скопировать текст в буфер обмена.');
        });
    }
}
