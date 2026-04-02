import sqlite3
import os

DB_FILE = 'circulars.db'

def get_connection():
    return sqlite3.connect(DB_FILE)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS circulars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            title TEXT UNIQUE,
            pdf_url TEXT,
            summary TEXT
        )
    ''')
    conn.commit()
    conn.close()

def insert_circular(date, title, pdf_url):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO circulars (date, title, pdf_url)
            VALUES (?, ?, ?)
        ''', (date, title, pdf_url))
        conn.commit()
        inserted = True
    except sqlite3.IntegrityError:
        inserted = False  # Already exists
    finally:
        conn.close()
    return inserted

def get_all_circulars():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM circulars')
    rows = cursor.fetchall()
    conn.close()
    
    circulars = []
    for row in rows:
        circulars.append({
            'id': row[0],
            'date': row[1],
            'title': row[2],
            'pdf_url': row[3],
            'summary': row[4]
        })
    return circulars

def save_summary(circular_id, summary_text):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE circulars SET summary = ? WHERE id = ?
    ''', (summary_text, circular_id))
    conn.commit()
    conn.close()

def delete_summary(circular_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE circulars SET summary = NULL WHERE id = ?
    ''', (circular_id,))
    conn.commit()
    conn.close()

def get_circular_by_title(title):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM circulars WHERE title = ?', (title,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            'id': row[0],
            'date': row[1],
            'title': row[2],
            'pdf_url': row[3],
            'summary': row[4]
        }
    return None

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
