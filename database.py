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
            image_url TEXT NOT NULL
        )
    ''')
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
    cursor.execute('SELECT * FROM products')
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_product_by_id(product_id):
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
    row = cursor.fetchone()
    conn.close()
    return row