import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'museum.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Create Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            email TEXT UNIQUE,
            password_hash TEXT,
            otp TEXT,
            is_verified BOOLEAN DEFAULT 0,
            full_name TEXT
        )
    ''')

    # Create Exhibitions table
    c.execute('''
        CREATE TABLE IF NOT EXISTS exhibitions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            availability_status TEXT DEFAULT 'Open'
        )
    ''')
    
    # Create Bookings table
    c.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            visitor_name TEXT,
            visit_date TEXT,
            exhibition_id INTEGER,
            num_tickets INTEGER,
            total_price REAL,
            ticket_hash TEXT,
            status TEXT DEFAULT 'Pending Payment',
            razorpay_order_id TEXT,
            razorpay_payment_id TEXT,
            razorpay_signature TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(exhibition_id) REFERENCES exhibitions(id)
        )
    ''')
    
    # Insert some mock exhibitions
    c.execute('SELECT COUNT(*) FROM exhibitions')
    if c.fetchone()[0] == 0:
        exhibitions = [
            ("National Science Centre, New Delhi", "Premier science museum in the capital with interactive galleries.", 100.0),
            ("Nehru Science Centre, Mumbai", "India's largest interactive science center located in Worli.", 100.0),
            ("BITM Kolkata", "The first science museum in India, focusing on industrial and technological heritage.", 100.0),
            ("Science City, Ahmedabad", "A large-scale science center featuring an IMAX theater and pavilion.", 100.0)
        ]
        c.executemany('INSERT INTO exhibitions (title, description, price) VALUES (?, ?, ?)', exhibitions)
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully.")
