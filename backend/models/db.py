import sqlite3, os

def get_db():
    db_path = os.path.join(os.path.dirname(__file__), "..", "tech_service.db")
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn
