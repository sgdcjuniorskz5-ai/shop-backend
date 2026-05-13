let tg = window.Telegram.WebApp;
tg.expand();

function buyProduct(name, price) {
    const data = {
        item: name,
        price: price
    };
    // Отправляем данные в бот
    tg.sendData(JSON.stringify(data));
}