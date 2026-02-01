# pages/driver.py
import streamlit as st
from utils.pdf.daily_report_pdf import generate_daily_report_pdf
import os
from utils.auth import logout, require_driver, require_admin
from utils.db import get_connection
from datetime import date, datetime


def driver_ui(driver_login_id: str | None = None):
    conn = get_connection()
    conn.row_factory = None
    c = conn.cursor()

    # 管理者閲覧 or 通常ドライバー
    is_admin_view = driver_login_id is not None

    if is_admin_view:
        require_admin()
        user = c.execute("""
            SELECT d.id, d.driver_name, u.login_id
            FROM drivers d
            JOIN users u ON u.driver_id = d.id
            WHERE u.login_id = ?
        """, (driver_login_id,)).fetchone()
        if not user:
            st.error("ドライバーが存在しません")
            return
        driver_id, driver_name, login_id = user
    else:
        require_driver()
        user = st.session_state.user
        driver_id = user["driver_id"]
        driver_name = user["driver_name"]
        login_id = user["login_id"]

    st.title(f"🚚 ドライバー画面：{login_id}｜{driver_name}")

    if not is_admin_view and st.button("ログアウト"):
        logout()
        st.switch_page("app.py")

    today = date.today().strftime("%Y-%m-%d")

    # ==================================================
    # ① 日常点検（〇×）
    # ==================================================
    st.divider()
    st.subheader("📋 日常点検（〇×形式）")

    row = c.execute("""
        SELECT * FROM daily_checks
        WHERE driver_id=? AND record_date=?
    """, (driver_id, today)).fetchone()

    daily_check = dict(zip([d[0] for d in c.description], row)) if row else {}

    def maru_batsu(label, val=None):
        default = 1 if val is None else val
        return st.radio(
            label,
            [1, 0],
            format_func=lambda x: "〇（異常なし）" if x == 1 else "×（異常あり）",
            horizontal=True,
            index=0 if default == 1 else 1
        )

    with st.form("daily_check_form"):
        brake = maru_batsu("🛑 ブレーキ", daily_check.get("brake"))
        tire  = maru_batsu("🚗 タイヤ", daily_check.get("tire"))
        light = maru_batsu("💡 灯火類", daily_check.get("light"))
        other = st.text_area("備考", value=daily_check.get("other", ""))

        if st.form_submit_button("登録 / 更新"):
            c.execute("""
                INSERT INTO daily_checks
                (driver_id, record_date, brake, tire, light, other, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(driver_id, record_date)
                DO UPDATE SET
                    brake=excluded.brake,
                    tire=excluded.tire,
                    light=excluded.light,
                    other=excluded.other,
                    created_by=excluded.created_by
            """, (
                driver_id, today, brake, tire, light, other,
                "admin" if is_admin_view else "driver"
            ))
            conn.commit()
            st.success("日常点検を保存しました")

    # ==================================================
    # ② 乗務前点呼（※ 日常点検実施確認あり）
    # ==================================================
    st.divider()
    st.subheader("🚨 乗務前点呼（出庫前）")

    row = c.execute("""
        SELECT * FROM tenko_records
        WHERE driver_id=? AND record_date=? AND timing='before'
    """, (driver_id, today)).fetchone()

    before = dict(zip([d[0] for d in c.description], row)) if row else {}

    with st.form("tenko_before_form"):
        record_time = st.time_input(
            "点呼時刻",
            value=datetime.strptime(
                before.get("record_time", datetime.now().strftime("%H:%M")),
                "%H:%M"
            ).time()
        ).strftime("%H:%M")

        health_list = ["良好", "やや不調", "不調"]
        health = st.selectbox(
            "健康状態",
            health_list,
            index=health_list.index(before.get("health"))
            if before.get("health") in health_list else 0
        )

        alcohol = st.number_input(
            "アルコール検知値（mg/L）",
            min_value=0.0,
            step=0.01,
            value=before.get("alcohol", 0.0)
        )

        daily_check_done = st.radio(
            "🔧 日常点検の実施確認",
            [1, 0],
            format_func=lambda x: "実施済" if x == 1 else "未実施",
            horizontal=True,
            index=0 if before.get("daily_check_done", 1) == 1 else 1
        )

        checker = st.text_input(
            "点呼執行者",
            value=before.get("checker", driver_name)
        )

        memo = st.text_area("備考", value=before.get("memo", ""))

        if st.form_submit_button("登録 / 更新"):
            c.execute("""
                INSERT INTO tenko_records
                (driver_id, record_date, timing, record_time,
                 health, alcohol, daily_check_done, checker, memo, created_by)
                VALUES (?, ?, 'before', ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(driver_id, record_date, timing)
                DO UPDATE SET
                    record_time=excluded.record_time,
                    health=excluded.health,
                    alcohol=excluded.alcohol,
                    daily_check_done=excluded.daily_check_done,
                    checker=excluded.checker,
                    memo=excluded.memo,
                    created_by=excluded.created_by
            """, (
                driver_id, today, record_time,
                health, alcohol, daily_check_done,
                checker, memo,
                "admin" if is_admin_view else "driver"
            ))
            conn.commit()
            st.success("乗務前点呼を保存しました")

    # ==================================================
    # ③ 乗務後点呼
    # ==================================================
    st.divider()
    st.subheader("🚨 乗務後点呼（帰庫後）")

    row = c.execute("""
        SELECT * FROM tenko_records
        WHERE driver_id=? AND record_date=? AND timing='after'
    """, (driver_id, today)).fetchone()

    after = dict(zip([d[0] for d in c.description], row)) if row else {}

    with st.form("tenko_after_form"):
        record_time = st.time_input(
            "点呼時刻",
            value=datetime.strptime(
                after.get("record_time", datetime.now().strftime("%H:%M")),
                "%H:%M"
            ).time()
        ).strftime("%H:%M")

        health_list = ["良好", "やや不調", "不調"]
        health = st.selectbox(
            "健康状態",
            health_list,
            index=health_list.index(after.get("health"))
            if after.get("health") in health_list else 0
        )

        alcohol = st.number_input(
            "アルコール検知値（mg/L）",
            min_value=0.0,
            step=0.01,
            value=after.get("alcohol", 0.0)
        )

        checker = st.text_input(
            "点呼執行者",
            value=after.get("checker", driver_name)
        )

        memo = st.text_area("備考", value=after.get("memo", ""))

        if st.form_submit_button("登録 / 更新"):
            c.execute("""
                INSERT INTO tenko_records
                (driver_id, record_date, timing, record_time,
                 health, alcohol, checker, memo, created_by)
                VALUES (?, ?, 'after', ?, ?, ?, ?, ?, ?)
                ON CONFLICT(driver_id, record_date, timing)
                DO UPDATE SET
                    record_time=excluded.record_time,
                    health=excluded.health,
                    alcohol=excluded.alcohol,
                    checker=excluded.checker,
                    memo=excluded.memo,
                    created_by=excluded.created_by
            """, (
                driver_id, today, record_time,
                health, alcohol, checker, memo,
                "admin" if is_admin_view else "driver"
            ))
            conn.commit()
            st.success("乗務後点呼を保存しました")

    # ==================================================
    # ④ 運転日報
    # ==================================================
    st.divider()
    st.subheader("📝 運転日報")

    row = c.execute("""
        SELECT * FROM daily_reports
        WHERE driver_id=? AND record_date=?
    """, (driver_id, today)).fetchone()

    report = dict(zip([d[0] for d in c.description], row)) if row else {}

    with st.form("daily_report_form"):
        start_time = st.time_input(
            "開始時間",
            value=datetime.strptime(
                report.get("start_time", datetime.now().strftime("%H:%M")),
                "%H:%M"
            ).time()
        ).strftime("%H:%M")

        end_time = st.time_input(
            "終了時間",
            value=datetime.strptime(
                report.get("end_time", datetime.now().strftime("%H:%M")),
                "%H:%M"
            ).time()
        ).strftime("%H:%M")

        mileage = st.number_input(
            "走行距離（km）",
            min_value=0,
            value=report.get("mileage", 0)
        )

        note = st.text_area("備考", value=report.get("note", ""))

        if st.form_submit_button("登録 / 更新"):
            c.execute("""
                INSERT INTO daily_reports
                (driver_id, record_date, start_time, end_time, mileage, note, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(driver_id, record_date)
                DO UPDATE SET
                    start_time=excluded.start_time,
                    end_time=excluded.end_time,
                    mileage=excluded.mileage,
                    note=excluded.note,
                    created_by=excluded.created_by
            """, (
                driver_id, today, start_time, end_time, mileage, note,
                "admin" if is_admin_view else "driver"
            ))
            conn.commit()
            st.success("運転日報を保存しました")

    # ==================================================
    # ⑤ 日別PDF
    # ==================================================
    st.divider()
    st.subheader("📄 日別PDF（点呼・点検・日報）")

    pdf_date = st.date_input("日付", value=date.today()).strftime("%Y-%m-%d")

    if st.button("📄 PDFを生成"):
        pdf_path = generate_daily_report_pdf(driver_id, pdf_date)
        with open(pdf_path, "rb") as f:
            st.download_button(
                "⬇ PDFダウンロード",
                f,
                file_name=os.path.basename(pdf_path),
                mime="application/pdf"
            )

    conn.close()


if __name__ == "__main__":
    driver_ui()
