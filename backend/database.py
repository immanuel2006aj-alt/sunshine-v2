import sqlite3
import json
from datetime import datetime
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'users.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE,
                password TEXT,
                upi TEXT,
                usdt TEXT,
                balance INTEGER DEFAULT 0,
                days INTEGER DEFAULT 0,
                daily_captcha_count INTEGER DEFAULT 0,
                last_active TEXT,
                status TEXT DEFAULT 'Active',
                notes TEXT
            )
        ''')
        conn.commit()

# Initialize DB on import
init_db()

# --- CRUD functions ---

async def get_user_by_username(username):
    try:
        with get_db() as conn:
            cur = conn.execute("SELECT * FROM users WHERE username = ?", (username,))
            row = cur.fetchone()
            if row:
                return dict(row)
            return None
    except Exception as e:
        print(f"[DB] get_user_by_username error: {e}")
        return None

async def get_user_by_id(user_id):
    try:
        with get_db() as conn:
            cur = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cur.fetchone()
            if row:
                return dict(row)
            return None
    except Exception as e:
        print(f"[DB] get_user_by_id error: {e}")
        return None

async def create_user(data):
    try:
        with get_db() as conn:
            conn.execute('''
                INSERT INTO users (id, username, password, upi, usdt, balance, days, daily_captcha_count, last_active, status, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['id'],
                data['username'],
                data['password'],
                data['upi'],
                data['usdt'],
                data['balance'],
                data['days'],
                data['daily_captcha_count'],
                data['last_active'],
                data['status'],
                data['notes']
            ))
            conn.commit()
            return True
    except Exception as e:
        print(f"[DB] create_user error: {e}")
        return None

async def update_user(user_id, updates):
    try:
        with get_db() as conn:
            # Build SET clause dynamically
            set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
            values = list(updates.values()) + [user_id]
            conn.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
            conn.commit()
            return True
    except Exception as e:
        print(f"[DB] update_user error: {e}")
        return False

async def check_and_reset_streak(user_id):
    try:
        user = await get_user_by_id(user_id)
        if not user:
            return None
        last_active_str = user.get('last_active')
        if last_active_str:
            try:
                last_active = datetime.fromisoformat(last_active_str)
                today = datetime.now().date()
                if last_active.date() < today:
                    await update_user(user_id, {
                        'days': 0,
                        'daily_captcha_count': 0,
                        'last_active': datetime.now().isoformat()
                    })
                    user = await get_user_by_id(user_id)
            except:
                pass
        return user
    except Exception as e:
        print(f"[DB] check_and_reset_streak error: {e}")
        return None
