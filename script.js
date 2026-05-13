let tg = window.Telegram.WebApp;
tg.expand();

function setQty(id, value) {
    document.getElementById(id).value = value;
}

function prepareOrder(name, pricePerOne, qtyId) {
    const qty = document.getElementById(qtyId).value;
    const totalPrice = pricePerOne * qty;
    
    const data = {
        item: name,
        quantity: qty,
        price: totalPrice
    };
    
    tg.sendData(JSON.stringify(data));
}