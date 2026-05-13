import sqlite3

# Функция для создания базы данных и таблиц
def init_db():
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    # Создаем таблицу товаров
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            description TEXT,
            image_id TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print("База данных готова!")

# Функция для добавления нового товара
def add_product(name, price, description, image_id):
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO products (name, price, description, image_id) VALUES (?, ?, ?, ?)',
                   (name, price, description, image_id))
    conn.commit()
    conn.close()