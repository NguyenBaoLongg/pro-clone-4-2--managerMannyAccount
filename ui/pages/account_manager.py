import streamlit as st
import time
from ui.utils import load_json, save_json, ACCOUNTS_FILE

def render_account_manager():
    st.markdown("## 👤 Quản lý Tài khoản TikTok")
    data = load_json(ACCOUNTS_FILE)
    acc_list = data.get("accounts", [])

    with st.expander("➕ Thêm Tài khoản Mới", expanded=False):
        c1, c2, c3 = st.columns(3)
        email = c1.text_input("Email/User:", key="new_acc_email")
        pwd = c2.text_input("Password:", type="password", key="new_acc_pwd")
        tid = c3.text_input("TikTok ID (@abc):", key="new_acc_id")

        if st.button("Lưu Tài khoản", type="primary"):
            if email and tid:
                if any(a['email'] == email for a in acc_list): st.error("Email trùng!")
                else:
                    acc_list.append({"email": email, "password": pwd, "tiktok_id": tid, "active": True})
                    save_json(ACCOUNTS_FILE, {"accounts": acc_list})
                    st.success("Đã thêm!"); time.sleep(1); st.rerun()
            else: st.warning("Nhập thiếu thông tin.")

    st.divider()
    st.subheader(f"📋 Danh sách ({len(acc_list)})")
    if acc_list:
        for i, acc in enumerate(acc_list):
            with st.expander(f"**{i+1}. {acc.get('tiktok_id')}** ({acc.get('email')})"):
                with st.form(key=f"form_edit_acc_{i}"):
                    c_e1, c_e2, c_e3 = st.columns(3)
                    e_mail = c_e1.text_input("Email", value=acc.get('email'))
                    e_pass = c_e2.text_input("Pass", value=acc.get('password'), type="password")
                    e_tid = c_e3.text_input("ID", value=acc.get('tiktok_id'))

                    c_save, c_del = st.columns([1, 1])
                    if c_save.form_submit_button("💾 Cập nhật"):
                        acc_list[i] = {"email": e_mail, "password": e_pass, "tiktok_id": e_tid, "active": acc.get("active", True)}
                        save_json(ACCOUNTS_FILE, {"accounts": acc_list})
                        st.success("Đã cập nhật!"); time.sleep(0.5); st.rerun()
                    if c_del.form_submit_button("🗑️ Xóa Nick", type="primary"):
                        acc_list.pop(i)
                        save_json(ACCOUNTS_FILE, {"accounts": acc_list})
                        st.rerun()
    else: st.info("Trống.")