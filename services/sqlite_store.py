import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SQLITE_DB_PATH = BASE_DIR / 'quiz_app.db'


def get_sqlite_connection() -> sqlite3.Connection:
    return sqlite3.connect(SQLITE_DB_PATH)


def init_db() -> None:
    conn = get_sqlite_connection()
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            class_level TEXT NOT NULL,
            stream TEXT NOT NULL,
            assigned_set TEXT NOT NULL,
            login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS test_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT NOT NULL,
            class_level TEXT NOT NULL,
            stream TEXT NOT NULL,
            assigned_set TEXT NOT NULL,
            score INTEGER NOT NULL,
            total_questions INTEGER NOT NULL,
            tab_switches INTEGER DEFAULT 0,
            submission_type TEXT,
            test_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS set_counter (
            id INTEGER PRIMARY KEY,
            class_level TEXT NOT NULL,
            stream TEXT NOT NULL,
            current_set_index INTEGER DEFAULT 0,
            UNIQUE(class_level, stream)
        )
    ''')

    conn.commit()
    conn.close()
