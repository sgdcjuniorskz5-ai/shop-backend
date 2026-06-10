import sqlite3

def init_db():
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            description TEXT,
            image_url TEXT NOT NULL,
            discount INTEGER DEFAULT 0
        )
    ''')
    # Добавляем колонку discount, если её нет (для старых БД)
    try:
        cursor.execute('ALTER TABLE products ADD COLUMN discount INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

def add_product(name, price, description, image_url):
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO products (name, price, description, image_url) VALUES (?, ?, ?, ?)',
                   (name, price, description, image_url))
    conn.commit()
    conn.close()

def delete_product(product_id):
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
    conn.commit()
    conn.close()

def get_all_products():
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, price, description, image_url, discount FROM products')
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_product_by_id(product_id):
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, price, description, image_url, discount FROM products WHERE id = ?', (product_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def set_discount(product_id, percent):
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE products SET discount = ? WHERE id = ?', (percent, product_id))
    conn.commit()
    conn.close()

def remove_discount(product_id):
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE products SET discount = 0 WHERE id = ?', (product_id,))
    conn.commit()
    conn.close()
