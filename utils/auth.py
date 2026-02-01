# utils/auth.py
import streamlit as st
from utils.db import get_connection

# =========================
# ログイン処理（QR / 通常共通）
# =========================
def login(login_id: str):
    conn = get_connection()
    c = conn.cursor()

    # ★ is_active = 1 を必ず条件に入れる
    user = c.execute("""
        SELECT
            u.login_id,
            u.role,
            d.id   AS driver_id,
            d.driver_name,
            d.is_active
        FROM users u
        LEFT JOIN drivers d ON u.driver_id = d.id
        WHERE u.login_id = ?
          AND (u.role = 'admin' OR d.is_active = 1)
    """, (login_id,)).fetchone()

    conn.close()

    if not user:
        st.error("ログインできません（無効なアカウント、または停止中）")
        return False

    # ★ セッションに is_active を保存
    st.session_state.user = {
        "login_id": user["login_id"],
        "role": user["role"],
        "driver_id": user["driver_id"],
        "driver_name": user["driver_name"],
        "is_active": user["is_active"] if user["role"] == "driver" else 1
    }

    return True


# =========================
# ログアウト
# =========================
def logout():
    st.session_state.clear()


# =========================
# 管理者チェック
# =========================
def require_admin():
    if "user" not in st.session_state:
        st.switch_page("app.py")
        st.stop()

    if st.session_state.user["role"] != "admin":
        st.error("管理者権限が必要です")
        st.stop()


# =========================
# ドライバーチェック（二重チェック）
# =========================
def require_driver():
    if "user" not in st.session_state:
        st.switch_page("app.py")
        st.stop()

    user = st.session_state.user

    if user["role"] != "driver":
        st.error("ドライバー権限が必要です")
        st.stop()

    # ★ 二重チェック（超重要）
    if user.get("is_active") != 1:
        st.error("このドライバーは無効化されています")
        st.stop()
