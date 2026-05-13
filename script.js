let tg = window.Telegram.WebApp;
tg.expand();

const API_URL = '/api/products';
const productsContainer = document.querySelector('.products-grid');

// Загружаем товары при загрузке страницы
document.addEventListener('DOMContentLoaded', loadProducts);

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

function prepareOrder(name, pricePerOne, qtyId, productId) {
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
    
    tg.sendData(JSON.stringify(data));
}