const tg = window.Telegram?.WebApp;
const isWebApp = !!tg;

if (tg) {
    tg.expand();
}

const productsContainer = document.querySelector('.products-grid');
const metaApi = document.querySelector('meta[name="api-base"]');
const API_BASE = metaApi && metaApi.content && metaApi.content.trim()
    ? metaApi.content.trim().replace(/\/$/, '')
    : (window.location.protocol === 'file:' ? 'http://localhost:8080/api' : `${window.location.origin}/api`);
const API_URL = `${API_BASE}/products`;

let pendingOrder = null;

if (window.location.protocol === 'file:') {
    productsContainer.innerHTML = '<p style="text-align: center; grid-column: 1/-1; color: red;">Откройте магазин через локальный сервер: <strong>http://localhost:8080/</strong></p>';
}

document.addEventListener('DOMContentLoaded', () => {
    loadProducts();
    const refreshBtn = document.getElementById('refresh-btn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', loadProducts);
    }

    const modalCancel = document.getElementById('modal-cancel');
    const modalConfirm = document.getElementById('modal-confirm');
    if (modalCancel) modalCancel.addEventListener('click', closeModal);
    if (modalConfirm) modalConfirm.addEventListener('click', confirmOrder);
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

function prepareOrder(name, pricePerOne, qtyId, productId) {
    const qtyElement = document.getElementById(qtyId);
    const qty = parseInt(qtyElement.value);
    
    if (isNaN(qty) || qty <= 0) {
        alert('❌ Пожалуйста, укажите корректное количество!');
        return;
    }
    
    const totalPrice = pricePerOne * qty;
    
    pendingOrder = {
        product_id: productId,
        item: name,
        quantity: qty,
        price: totalPrice
    };

    const orderInfo = document.getElementById('modal-order-info');
    orderInfo.innerHTML = `
        <div class="info-item">
            <span class="info-label">Товар:</span>
            <span class="info-value">${name}</span>
        </div>
        <div class="info-item">
            <span class="info-label">Количество:</span>
            <span class="info-value">${qty} шт.</span>
        </div>
        <div class="info-item">
            <span class="info-label">Цена за шт:</span>
            <span class="info-value">${pricePerOne} ₸</span>
        </div>
        <div class="info-item info-total">
            <span class="info-label">Итого:</span>
            <span class="info-value">${totalPrice} ₸</span>
        </div>
    `;

    const nameInput = document.getElementById('modal-name');
    const addressInput = document.getElementById('modal-address');
    
    if (isWebApp && tg.initDataUnsafe?.user) {
        const user = tg.initDataUnsafe.user;
        nameInput.value = `${user.first_name || ''} ${user.last_name || ''}`.trim();
    } else {
        nameInput.value = '';
    }
    addressInput.value = '';
    nameInput.classList.remove('error');
    addressInput.classList.remove('error');

    document.getElementById('order-modal').classList.add('active');
}

function closeModal() {
    document.getElementById('order-modal').classList.remove('active');
    pendingOrder = null;
}

function showToast(message) {
    const toast = document.getElementById("toast");
    toast.textContent = message;
    toast.className = "toast show";
    setTimeout(() => { toast.className = toast.className.replace("show", ""); }, 3000);
}

async function confirmOrder() {
    const nameInput = document.getElementById('modal-name');
    const addressInput = document.getElementById('modal-address');
    
    const name = nameInput.value.trim();
    const address = addressInput.value.trim();
    
    let hasError = false;
    
    if (!name) {
        nameInput.classList.add('error');
        hasError = true;
    } else {
        nameInput.classList.remove('error');
    }
    
    if (!address) {
        addressInput.classList.add('error');
        hasError = true;
    } else {
        addressInput.classList.remove('error');
    }
    
    if (hasError) {
        return;
    }
    
    if (!pendingOrder) {
        alert('❌ Ошибка: данные заказа не найдены.');
        return;
    }
    
    const data = {
        ...pendingOrder,
        name: name,
        address: address
    };

    if (isWebApp && tg) {
        tg.sendData(JSON.stringify(data));
        showToast("Инструкция отправлена в чат с ботом!");
    } else {
        showToast("Заказ оформлен! Откройте бота, чтобы получить реквизиты.");
        console.log("Order Data:", data);
    }
    closeModal();
}
