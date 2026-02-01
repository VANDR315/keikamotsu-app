# check_columns.py
import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), "tenko.db")
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

cols = c.execute("PRAGMA table_info(tenko_records)").fetchall()
for col in cols:
    print(col)

conn.close()
