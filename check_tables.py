import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "tenko.db")

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

tables = c.execute("""
SELECT name FROM sqlite_master
WHERE type='table'
""").fetchall()

print("📦 テーブル一覧:")
for t in tables:
    print("-", t[0])

conn.close()
