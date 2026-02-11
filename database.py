import sqlite3
from datetime import datetime

class Database:
    def __init__(self, db_name='bot.db'):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def create_tables(self):
        # Таблица пользователей
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                phone TEXT,
                user_type TEXT,
                registered_date TEXT
            )
        ''')
        
        # Таблица заявок
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS requests (
                request_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                user_type TEXT,
                city TEXT,
                object_type TEXT,
                work_type TEXT,
                budget_range TEXT,
                square_meters INTEGER,
                description TEXT,
                status TEXT DEFAULT 'active',
                created_date TEXT
            )
        ''')
        
        # Таблица совпадений
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS matches (
                match_id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER,
                matched_request_id INTEGER,
                match_score REAL,
                viewed BOOLEAN DEFAULT 0,
                created_date TEXT
            )
        ''')
        
        self.conn.commit()
    
    def add_user(self, user_id, username, full_name, user_type, phone=None):
        date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.cursor.execute('''
            INSERT OR REPLACE INTO users (user_id, username, full_name, phone, user_type, registered_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, username, full_name, phone, user_type, date))
        self.conn.commit()
    
    def add_request(self, user_id, user_type, city, object_type, work_type, 
                   budget_range, square_meters, description):
        date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.cursor.execute('''
            INSERT INTO requests 
            (user_id, user_type, city, object_type, work_type, budget_range, 
             square_meters, description, created_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, user_type, city, object_type, work_type, budget_range, 
              square_meters, description, date))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_user_requests(self, user_id):
        self.cursor.execute('SELECT * FROM requests WHERE user_id = ? ORDER BY created_date DESC', (user_id,))
        return self.cursor.fetchall()
    
    def get_active_requests(self, user_type=None):
        query = 'SELECT * FROM requests WHERE status = "active"'
        if user_type:
            query += f' AND user_type = "{user_type}"'
        self.cursor.execute(query)
        return self.cursor.fetchall()
    
    def save_match(self, request_id, matched_request_id, match_score):
        date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.cursor.execute('''
            INSERT INTO matches (request_id, matched_request_id, match_score, created_date)
            VALUES (?, ?, ?, ?)
        ''', (request_id, matched_request_id, match_score, date))
        self.conn.commit()
    
    def get_matches_for_request(self, request_id, limit=10):
        self.cursor.execute('''
            SELECT m.*, r.* FROM matches m
            JOIN requests r ON m.matched_request_id = r.request_id
            WHERE m.request_id = ? AND m.viewed = 0
            ORDER BY m.match_score DESC
            LIMIT ?
        ''', (request_id, limit))
        return self.cursor.fetchall()
    
    def mark_match_viewed(self, match_id):
        self.cursor.execute('UPDATE matches SET viewed = 1 WHERE match_id = ?', (match_id,))
        self.conn.commit()
    
    def close_request(self, request_id):
        self.cursor.execute('UPDATE requests SET status = "closed" WHERE request_id = ?', (request_id,))
        self.conn.commit()
