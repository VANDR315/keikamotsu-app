import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "tenko.db")

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

c.execute("""
ALTER TABLE tenko_records
ADD COLUMN daily_check_done INTEGER DEFAULT 1
""")

conn.commit()
conn.close()

print("✅ daily_check_done カラムを追加しました")
