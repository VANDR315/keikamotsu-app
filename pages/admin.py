# pages/admin.py
import streamlit as st
from datetime import date, datetime
from utils.auth import logout, require_admin
from utils.db import get_connection
from utils.qr import generate_login_qr
from utils.pdf.daily_report_pdf import generate_daily_report_pdf
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
import os

require_admin()

st.set_page_config(page_title="管理者画面", layout="wide")
st.title("🛠 管理者画面")
st.caption(f"ログイン中：{st.session_state.user['login_id']}")

# -------------------------
# ログアウト
# -------------------------
if st.button("ログアウト"):
    logout()
    st.rerun()

conn = get_connection()
c = conn.cursor()

# =========================
# ドライバー登録
# =========================
st.divider()
st.subheader("👤 新規ドライバー登録")

company_name = st.text_input("会社名")
driver_name  = st.text_input("ドライバー名")
driver_code  = st.text_input("業務ID（ログインID）")

if st.button("登録"):
    if company_name and driver_name and driver_code:
        c.execute("INSERT INTO companies (company_name) VALUES (?)", (company_name,))
        company_id = c.lastrowid
        c.execute(
            "INSERT INTO drivers (company_id, driver_code, driver_name, is_active) VALUES (?, ?, ?, 1)",
            (company_id, driver_code, driver_name)
        )
        driver_id = c.lastrowid
        c.execute(
            "INSERT INTO users (login_id, role, driver_id) VALUES (?, 'driver', ?)",
            (driver_code, driver_id)
        )
        conn.commit()
        st.success("ドライバーを登録しました")
        st.rerun()
    else:
        st.error("すべて入力してください")

# =========================
# ドライバー管理
# =========================
st.divider()
st.subheader("📱 ドライバー管理")

drivers = c.execute("""
    SELECT d.id, d.driver_name, u.login_id, d.is_active
    FROM drivers d
    JOIN users u ON u.driver_id = d.id
    ORDER BY d.id DESC
""").fetchall()

for d in drivers:
    with st.expander(f"🚚 {d['driver_name']}（{'有効' if d['is_active'] else '無効'}）"):
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if st.button("有効 / 無効切替", key=f"toggle_{d['id']}"):
                c.execute(
                    "UPDATE drivers SET is_active=? WHERE id=?",
                    (0 if d["is_active"] else 1, d["id"])
                )
                conn.commit()
                st.rerun()

        with col2:
            if st.button("QR表示", key=f"qr_{d['login_id']}"):
                st.image(generate_login_qr(d["login_id"]))

        with col3:
            if st.button("QR PDF", key=f"pdf_{d['login_id']}"):
                os.makedirs("temp", exist_ok=True)
                pdf_path = f"temp/qr_{d['login_id']}.pdf"
                qr_path = generate_login_qr(d["login_id"])
                pdf = canvas.Canvas(pdf_path, pagesize=A4)
                pdf.drawString(100, 800, "ドライバーQRログイン")
                pdf.drawString(100, 780, f"氏名：{d['driver_name']}")
                pdf.drawImage(ImageReader(qr_path), 100, 520, 200, 200)
                pdf.save()
                with open(pdf_path, "rb") as f:
                    st.download_button("⬇ ダウンロード", f, file_name=os.path.basename(pdf_path))

        with col4:
            confirm = st.checkbox("本当に削除する", key=f"confirm_{d['id']}")
            if st.button("🚨 完全削除", key=f"delete_{d['id']}", disabled=not confirm):
                c.execute("DELETE FROM tenko_records WHERE driver_id=?", (d["id"],))
                c.execute("DELETE FROM daily_checks WHERE driver_id=?", (d["id"],))
                c.execute("DELETE FROM daily_reports WHERE driver_id=?", (d["id"],))
                c.execute("DELETE FROM users WHERE driver_id=?", (d["id"],))
                c.execute("DELETE FROM drivers WHERE id=?", (d["id"],))
                conn.commit()
                st.success("完全削除しました")
                st.rerun()

# =========================
# 編集共通関数
# =========================
def maru_batsu(label, val=1):
    return st.radio(
        label,
        [1, 0],
        format_func=lambda x: "〇（異常なし）" if x == 1 else "×（異常あり）",
        horizontal=True,
        index=0 if val == 1 else 1
    )

# =========================
# 管理対象ドライバー選択
# =========================
st.divider()
st.subheader("🧑‍✈️ 編集対象ドライバー")

drivers = c.execute("SELECT id, driver_name FROM drivers").fetchall()
driver_map = {d["driver_name"]: d["id"] for d in drivers}

selected_driver = st.selectbox("ドライバー", driver_map.keys())
target_driver_id = driver_map[selected_driver]
target_date = st.date_input("日付", value=date.today()).strftime("%Y-%m-%d")

# =========================
# 日常点検（編集）
# =========================
st.divider()
st.subheader("📋 日常点検")

row = c.execute("""
    SELECT * FROM daily_checks
    WHERE driver_id=? AND record_date=?
""", (target_driver_id, target_date)).fetchone()

dc = dict(row) if row else {}

with st.form("admin_daily_check"):
    brake = maru_batsu("🛑 ブレーキ", dc.get("brake", 1))
    tire  = maru_batsu("🚗 タイヤ", dc.get("tire", 1))
    light = maru_batsu("💡 灯火類", dc.get("light", 1))
    other = st.text_area("備考", value=dc.get("other", ""))

    if st.form_submit_button("保存"):
        c.execute("""
            INSERT INTO daily_checks
            (driver_id, record_date, brake, tire, light, other, created_by)
            VALUES (?, ?, ?, ?, ?, ?, 'admin')
            ON CONFLICT(driver_id, record_date)
            DO UPDATE SET
                brake=excluded.brake,
                tire=excluded.tire,
                light=excluded.light,
                other=excluded.other,
                created_by='admin'
        """, (target_driver_id, target_date, brake, tire, light, other))
        conn.commit()
        st.success("日常点検を保存しました")

# =========================
# 乗務前点呼（編集）
# =========================
st.divider()
st.subheader("🚨 乗務前点呼")

row = c.execute("""
    SELECT * FROM tenko_records
    WHERE driver_id=? AND record_date=? AND timing='before'
""", (target_driver_id, target_date)).fetchone()

before = dict(row) if row else {}

with st.form("admin_tenko_before"):
    record_time = st.time_input(
        "点呼時刻",
        value=datetime.strptime(before.get("record_time", "09:00"), "%H:%M").time()
    ).strftime("%H:%M")

    health = st.selectbox("健康状態", ["良好", "やや不調", "不調"],
                          index=["良好", "やや不調", "不調"].index(before.get("health", "良好")))

    alcohol = st.number_input("アルコール", min_value=0.0, step=0.01,
                              value=before.get("alcohol", 0.0))

    daily_check_done = st.radio(
        "日常点検 実施有無",
        [1, 0],
        format_func=lambda x: "実施済" if x == 1 else "未実施",
        horizontal=True,
        index=0 if before.get("daily_check_done", 1) == 1 else 1
    )

    checker = st.text_input("点呼執行者", value=before.get("checker", "管理者"))
    memo = st.text_area("備考", value=before.get("memo", ""))

    if st.form_submit_button("保存"):
        c.execute("""
            INSERT INTO tenko_records
            (driver_id, record_date, timing, record_time, health, alcohol,
             daily_check_done, checker, memo, created_by)
            VALUES (?, ?, 'before', ?, ?, ?, ?, ?, ?, 'admin')
            ON CONFLICT(driver_id, record_date, timing)
            DO UPDATE SET
                record_time=excluded.record_time,
                health=excluded.health,
                alcohol=excluded.alcohol,
                daily_check_done=excluded.daily_check_done,
                checker=excluded.checker,
                memo=excluded.memo,
                created_by='admin'
        """, (target_driver_id, target_date, record_time,
              health, alcohol, daily_check_done, checker, memo))
        conn.commit()
        st.success("乗務前点呼を保存しました")

# =========================
# 乗務後点呼（編集）
# =========================
st.divider()
st.subheader("🚨 乗務後点呼")

row = c.execute("""
    SELECT * FROM tenko_records
    WHERE driver_id=? AND record_date=? AND timing='after'
""", (target_driver_id, target_date)).fetchone()

after = dict(row) if row else {}

with st.form("admin_tenko_after"):
    record_time = st.time_input(
        "点呼時刻",
        value=datetime.strptime(after.get("record_time", "18:00"), "%H:%M").time()
    ).strftime("%H:%M")

    health = st.selectbox("健康状態", ["良好", "やや不調", "不調"],
                          index=["良好", "やや不調", "不調"].index(after.get("health", "良好")))

    alcohol = st.number_input("アルコール", min_value=0.0, step=0.01,
                              value=after.get("alcohol", 0.0))

    checker = st.text_input("点呼執行者", value=after.get("checker", "管理者"))
    memo = st.text_area("備考", value=after.get("memo", ""))

    if st.form_submit_button("保存"):
        c.execute("""
            INSERT INTO tenko_records
            (driver_id, record_date, timing, record_time, health, alcohol,
             checker, memo, created_by)
            VALUES (?, ?, 'after', ?, ?, ?, ?, ?, 'admin')
            ON CONFLICT(driver_id, record_date, timing)
            DO UPDATE SET
                record_time=excluded.record_time,
                health=excluded.health,
                alcohol=excluded.alcohol,
                checker=excluded.checker,
                memo=excluded.memo,
                created_by='admin'
        """, (target_driver_id, target_date, record_time,
              health, alcohol, checker, memo))
        conn.commit()
        st.success("乗務後点呼を保存しました")

# =========================
# 運転日報（編集）
# =========================
st.divider()
st.subheader("📝 運転日報")

row = c.execute("""
    SELECT * FROM daily_reports
    WHERE driver_id=? AND record_date=?
""", (target_driver_id, target_date)).fetchone()

dr = dict(row) if row else {}

with st.form("admin_daily_report"):
    start_time = st.time_input(
        "開始時間",
        value=datetime.strptime(dr.get("start_time", "09:00"), "%H:%M").time()
    ).strftime("%H:%M")

    end_time = st.time_input(
        "終了時間",
        value=datetime.strptime(dr.get("end_time", "18:00"), "%H:%M").time()
    ).strftime("%H:%M")

    mileage = st.number_input("走行距離（km）", min_value=0, value=dr.get("mileage", 0))
    note = st.text_area("備考", value=dr.get("note", ""))

    if st.form_submit_button("保存"):
        c.execute("""
            INSERT INTO daily_reports
            (driver_id, record_date, start_time, end_time, mileage, note, created_by)
            VALUES (?, ?, ?, ?, ?, ?, 'admin')
            ON CONFLICT(driver_id, record_date)
            DO UPDATE SET
                start_time=excluded.start_time,
                end_time=excluded.end_time,
                mileage=excluded.mileage,
                note=excluded.note,
                created_by='admin'
        """, (target_driver_id, target_date, start_time, end_time, mileage, note))
        conn.commit()
        st.success("運転日報を保存しました")

# =========================
# 日別PDF
# =========================
st.divider()
st.subheader("📄 日別PDF")

if st.button("PDF生成"):
    pdf_path = generate_daily_report_pdf(target_driver_id, target_date)
    with open(pdf_path, "rb") as f:
        st.download_button("⬇ ダウンロード", f, file_name=os.path.basename(pdf_path))

conn.close()
