# app.py
import streamlit as st
from utils.auth import login

st.set_page_config(
    page_title="軽貨物安全対策アプリ",
    layout="centered"
)

# -------------------------
# セッション初期化
# -------------------------
if "user" not in st.session_state:
    st.session_state.user = None

# -------------------------
# QR 用クエリ取得
# -------------------------
params = st.query_params
preset_login_id = params.get("login_id", [None])[0]

# -------------------------
# 未ログイン → ログイン画面
# -------------------------
if st.session_state.user is None:
    st.title("🔐 ログイン")

    login_id = st.text_input(
        "ログインID",
        value=preset_login_id or ""
    )

    if st.button("ログイン"):
        if login(login_id):
            st.rerun()
        else:
            st.error("ログインIDが正しくありません")

    st.stop()

# -------------------------
# 🔐 セーフティチェック（重要）
# -------------------------
user = st.session_state.user

if (
    not isinstance(user, dict)
    or "role" not in user
    or "login_id" not in user
):
    st.session_state.user = None
    st.rerun()

# -------------------------
# 画面分岐
# -------------------------
if user["role"] == "admin":
    st.switch_page("pages/admin.py")
elif user["role"] == "driver":
    st.switch_page("pages/driver.py")
else:
    # 想定外ロール
    st.session_state.user = None
    st.rerun()
