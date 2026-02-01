import sqlite3

DB_PATH = "tenko.db"

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# is_active カラムを追加
try:
    c.execute("""
        ALTER TABLE drivers
        ADD COLUMN is_active INTEGER DEFAULT 1
    """)
    print("✅ is_active カラムを追加しました")
except sqlite3.OperationalError as e:
    print("⚠️ すでに追加済み、またはエラー:", e)

conn.commit()
conn.close()
