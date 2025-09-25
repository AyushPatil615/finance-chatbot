import sqlite3
import datetime

DB_NAME = "finance.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Transactions table
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  category TEXT,
                  amount REAL,
                  date TEXT)''')
    conn.commit()
    conn.close()

def add_transaction(category, amount, date=None):
    if date is None:
        date = datetime.date.today().isoformat()
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO transactions (category, amount, date) VALUES (?, ?, ?)",
              (category, amount, date))
    conn.commit()
    conn.close()

def get_all_transactions():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, category, amount, date FROM transactions ORDER BY date")
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "category": r[1], "amount": r[2], "date": r[3]} for r in rows]
