# init_db.py
# 軽貨物安全対策アプリ DB初期化（BLOCK1 最終確定版）
# ※ 初回のみ実行

import sqlite3

DB_PATH = "tenko.db"

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

c.executescript("""
PRAGMA foreign_keys = ON;

-- =========================
-- 会社
-- =========================
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL
);

-- =========================
-- ドライバー
-- driver_code = 業務ID / QR / PDF 用
-- =========================
CREATE TABLE IF NOT EXISTS drivers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    driver_code TEXT NOT NULL UNIQUE,
    driver_name TEXT NOT NULL,
    license_number TEXT,
    is_active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- =========================
-- ユーザー（ログイン管理）
-- role は admin / driver に統一
-- =========================
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    login_id TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL CHECK(role IN ('admin', 'driver')),
    driver_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (driver_id) REFERENCES drivers(id)
);

-- =========================
-- 点呼記録（乗務前・後）
-- =========================
CREATE TABLE IF NOT EXISTS tenko_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    driver_id INTEGER NOT NULL,
    record_date DATE NOT NULL,           -- ★ 同一日リンク
    record_time TIME NOT NULL,
    timing TEXT NOT NULL CHECK(timing IN ('before', 'after')),
    health TEXT,
    alcohol REAL,
    checker TEXT,
    memo TEXT,
    created_by TEXT NOT NULL CHECK(created_by IN ('admin', 'driver')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (driver_id) REFERENCES drivers(id),
    UNIQUE(driver_id, record_date, timing)
);

-- =========================
-- 日常点検
-- =========================
CREATE TABLE IF NOT EXISTS daily_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    driver_id INTEGER NOT NULL,
    record_date DATE NOT NULL,           -- ★ 同一日リンク
    brake INTEGER,
    tire INTEGER,
    light INTEGER,
    other TEXT,
    created_by TEXT NOT NULL CHECK(created_by IN ('admin', 'driver')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (driver_id) REFERENCES drivers(id),
    UNIQUE(driver_id, record_date)
);

-- =========================
-- 運転日報
-- =========================
CREATE TABLE IF NOT EXISTS daily_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    driver_id INTEGER NOT NULL,
    record_date DATE NOT NULL,           -- ★ 同一日リンク
    start_time TIME,
    end_time TIME,
    mileage INTEGER,
    note TEXT,
    created_by TEXT NOT NULL CHECK(created_by IN ('admin', 'driver')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (driver_id) REFERENCES drivers(id),
    UNIQUE(driver_id, record_date)
);

-- =========================
-- インデックス（検索・PDF生成用）
-- =========================
CREATE INDEX IF NOT EXISTS idx_tenko_driver_date
ON tenko_records (driver_id, record_date);

CREATE INDEX IF NOT EXISTS idx_check_driver_date
ON daily_checks (driver_id, record_date);

CREATE INDEX IF NOT EXISTS idx_report_driver_date
ON daily_reports (driver_id, record_date);
""")
# =========================
# 初期管理者ユーザー作成
# =========================
c.execute("""
INSERT OR IGNORE INTO users (login_id, role, driver_id)
VALUES (?, ?, NULL)
""", ("admin", "admin"))

conn.commit()
conn.close()

print("✅ DB初期化 完了（BLOCK1 完全確定）")
