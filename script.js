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
    
    let priceHtml = '';
    if (product.discount && product.discount > 0) {
        priceHtml = `
            <div class="card-price">
                <span class="old-price">${product.price} ₸</span>
                <span class="discount-badge">-${product.discount}%</span>
                <span class="new-price">${product.discounted_price} ₸ / шт.</span>
            </div>`;
    } else {
        priceHtml = `<div class="card-price">${product.price} ₸ / шт.</div>`;
    }
    
    card.innerHTML = `
        <img src="${product.image_url}" alt="${product.name}" onerror="this.src='https://via.placeholder.com/150/fce4ec/880e4f?text=no-image'">
        <div class="card-title">${product.name}</div>
        ${priceHtml}
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
        
        <button class="buy-btn" onclick="prepareOrder('${product.name}', ${product.price}, '${qtyId}', ${product.id}, ${product.discount || 0})">Купить</button>
    `;
    
    return card;
}

function setQty(id, value) {
    document.getElementById(id).value = value;
}

function prepareOrder(name, pricePerOne, qtyId, productId, productDiscount) {
    const qtyElement = document.getElementById(qtyId);
    const qty = parseInt(qtyElement.value);
    
    if (isNaN(qty) || qty <= 0) {
        alert('❌ Пожалуйста, укажите корректное количество!');
        return;
    }
    
    let finalPricePerOne = pricePerOne;
    let appliedDiscounts = [];
    
    // Скидка на товар (из БД)
    if (productDiscount && productDiscount > 0) {
        finalPricePerOne = pricePerOne * (100 - productDiscount) / 100;
        appliedDiscounts.push(`скидка на товар ${productDiscount}%`);
    }
    
    // Скидка за объём (5+ шт)
    const VOLUME_DISCOUNT_THRESHOLD = 5;
    const VOLUME_DISCOUNT_PERCENT = 10;
    let volumeDiscountApplied = false;
    if (qty >= VOLUME_DISCOUNT_THRESHOLD) {
        finalPricePerOne = finalPricePerOne * (100 - VOLUME_DISCOUNT_PERCENT) / 100;
        volumeDiscountApplied = true;
        appliedDiscounts.push(`скидка за объём ${VOLUME_DISCOUNT_PERCENT}%`);
    }
    
    const totalPrice = Math.round(finalPricePerOne * qty);
    
    pendingOrder = {
        product_id: productId,
        item: name,
        quantity: qty,
        price: totalPrice
    };

    const orderInfo = document.getElementById('modal-order-info');
    let discountHtml = '';
    if (appliedDiscounts.length > 0) {
        discountHtml = `
            <div class="info-item">
                <span class="info-label">Скидки:</span>
                <span class="info-value discount-value">${appliedDiscounts.join(', ')}</span>
            </div>`;
    }
    
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
            <span class="info-value">${Math.round(finalPricePerOne)} ₸</span>
        </div>
        ${discountHtml}
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

    const userId = tg?.initDataUnsafe?.user?.id;
    
    const data = {
        ...pendingOrder,
        name: name,
        address: address
    };
    
    if (userId) {
        data.user_id = userId;
    }

    try {
        const res = await fetch(`${API_BASE}/order`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        if (res.ok) {
            const json = await res.json();
            
            if (json.sent_to_chat) {
                showToast("✅ Инструкция отправлена вам в чат с ботом!");
                setTimeout(() => {
                    if (tg) tg.close();
                }, 2500);
            } else {
                showOrderInstructions(json);
            }
        } else {
            const errJson = await res.json().catch(() => ({}));
            showToast(`❌ Ошибка: ${errJson.error || 'Не удалось отправить заказ'}`);
        }
    } catch (err) {
        console.error('Order POST failed', err);
        showToast('❌ Ошибка сети при оформлении заказа.');
    }
    closeModal();
}

function showOrderInstructions(orderData) {
    const overlay = document.createElement('div');
    overlay.className = 'order-instructions-overlay';
    overlay.innerHTML = `
        <div class="order-instructions">
            <h3>✅ Заказ принят!</h3>
            <div class="instructions-details">
                <p><strong>Код заказа:</strong></p>
                <p class="code-value">${orderData.order_code}</p>
                <p><strong>Товар:</strong> ${orderData.item || '—'}</p>
                <p><strong>Количество:</strong> ${orderData.quantity || '—'} шт.</p>
                <p><strong>Сумма:</strong> ${orderData.total} ₸</p>
            </div>
            <hr>
            <div class="instructions-payment">
                <p><strong>💳 Kaspi:</strong></p>
                <p class="code-value">${orderData.kaspi_number}</p>
                <p>В комментарии к переводу укажите код <strong>${orderData.order_code}</strong></p>
                <p>Затем отправьте скриншот чека в Telegram бот.</p>
            </div>
            <button class="instructions-close" onclick="this.closest('.order-instructions-overlay').remove()">Закрыть</button>
        </div>
    `;
    document.body.appendChild(overlay);
}
