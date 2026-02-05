import streamlit as st
import time
import subprocess
import sys
import pandas as pd
import os
from ui.utils import (
    load_json, save_json, normalize_time_input,
    ACCOUNTS_FILE, TRACKING_FILE, SCHEDULE_FILE, SESSION_CONFIG_FILE, PROJECT_ROOT, CONFIG_DIR
)

def render_dashboard():
    st.markdown("## 🤖 Dashboard Điều khiển")
    st.caption("Chọn Tài khoản, Kênh nguồn & Cấu hình thời gian chạy.")

    # Load dữ liệu
    accounts_data = load_json(ACCOUNTS_FILE)
    tracking_data = load_json(TRACKING_FILE)
    schedule_data = load_json(SCHEDULE_FILE)

    if "crawl_times" not in schedule_data: schedule_data["crawl_times"] = ["07:00", "12:00"]
    if "nurture_windows" not in schedule_data: schedule_data["nurture_windows"] = []

    acc_list = accounts_data.get("accounts", [])
    chn_list = tracking_data if isinstance(tracking_data, list) else tracking_data.get("channels", [])

    for x in acc_list:
        if "active" not in x: x["active"] = False
    for x in chn_list:
        if "active" not in x: x["active"] = False

    # --- KHU VỰC 1: CHỌN ---
    col_left, col_right = st.columns([1, 1], gap="medium")

    with col_left:
        st.subheader("1. Chọn Tài khoản Chạy")
        if st.checkbox("✅ Chọn tất cả Tài khoản", key="dash_all_acc"):
            for acc in acc_list: acc["active"] = True

        if acc_list:
            df_acc = pd.DataFrame(acc_list)
            if "tiktok_id" not in df_acc.columns: df_acc["tiktok_id"] = "---"
            edited_acc = st.data_editor(
                df_acc[["active", "tiktok_id", "email"]],
                column_config={
                    "active": st.column_config.CheckboxColumn("Chọn", width="small"),
                    "tiktok_id": st.column_config.TextColumn("ID TikTok", disabled=True),
                    "email": st.column_config.TextColumn("Email", disabled=True),
                },
                hide_index=True, width="stretch", key="dash_editor_acc", height=250
            )
            updated = edited_acc.to_dict(orient="records")
            if updated != df_acc[["active", "tiktok_id", "email"]].to_dict(orient="records"):
                for i, row in enumerate(updated): acc_list[i]["active"] = row["active"]
                save_json(ACCOUNTS_FILE, {"accounts": acc_list})
        else: st.info("📭 Chưa có tài khoản.")

    with col_right:
        st.subheader("2. Chọn Kênh Clone")
        if st.checkbox("✅ Chọn tất cả Kênh Nguồn", key="dash_all_chn"):
            for ch in chn_list: ch["active"] = True

        if chn_list:
            df_chn = pd.DataFrame(chn_list)
            if "last_video_url" not in df_chn.columns: df_chn["last_video_url"] = ""
            edited_chn = st.data_editor(
                df_chn[["active", "channel_url", "last_video_url"]],
                column_config={
                    "active": st.column_config.CheckboxColumn("Chọn", width="small"),
                    "channel_url": st.column_config.LinkColumn("Link Kênh", validate="^https://.*"),
                    "last_video_url": st.column_config.TextColumn("Tiến độ", disabled=True)
                },
                hide_index=True, width="stretch", key="dash_editor_chn", height=250
            )
            updated_c = edited_chn.to_dict(orient="records")
            has_change = False
            for i, row in enumerate(updated_c):
                if chn_list[i]["active"] != row["active"]:
                    chn_list[i]["active"] = row["active"]; has_change=True
            if has_change: save_json(TRACKING_FILE, {"channels": chn_list})
        else: st.info("📭 Chưa có kênh nguồn.")

    st.markdown("---")

    # --- KHU VỰC 2: LỊCH TRÌNH ---
    with st.expander("⏰ Cài đặt Lịch trình (Giờ Quét & Giờ Nuôi)", expanded=True):
        sch_c1, sch_c2 = st.columns(2)

        # CỘT 1: GIỜ QUÉT
        with sch_c1:
            st.markdown("**🕵️ Giờ Quét Video (HH:MM)**")
            current_crawls = schedule_data.get("crawl_times", [])

            c_input, c_btn = st.columns([3, 1])
            new_crawl_raw = c_input.text_input("Thêm giờ:", placeholder="VD: 07:30", key="in_crawl")

            if c_btn.button("➕", key="btn_add_crawl"):
                normalized_time = normalize_time_input(new_crawl_raw)
                if normalized_time:
                    if normalized_time not in current_crawls:
                        current_crawls.append(normalized_time)
                        current_crawls.sort()
                        schedule_data["crawl_times"] = current_crawls
                        save_json(SCHEDULE_FILE, schedule_data)
                        st.success(f"Đã thêm: {normalized_time}")
                        time.sleep(0.5); st.rerun()
                    else: st.warning("Giờ này đã có rồi.")
                else: st.error("Sai định dạng! Hãy nhập HH:MM")

            if current_crawls:
                st.write("Danh sách giờ:")
                cols = st.columns(4)
                for i, t in enumerate(current_crawls):
                    if cols[i % 4].button(f"{t} ❌", key=f"del_c_{t}"):
                        current_crawls.remove(t)
                        schedule_data["crawl_times"] = current_crawls
                        save_json(SCHEDULE_FILE, schedule_data)
                        st.rerun()
            else: st.caption("Chưa đặt giờ quét.")

        # CỘT 2: GIỜ NUÔI
        with sch_c2:
            st.markdown("**🍵 Khung Giờ Nuôi Nick**")
            current_wins = schedule_data.get("nurture_windows", [])

            n1, n2, n3 = st.columns([2, 2, 1])
            n_start_raw = n1.text_input("Bắt đầu:", placeholder="09:00", key="in_n_start")
            n_end_raw = n2.text_input("Kết thúc:", placeholder="11:00", key="in_n_end")

            if n3.button("➕", key="btn_add_win"):
                s_norm = normalize_time_input(n_start_raw)
                e_norm = normalize_time_input(n_end_raw)

                if s_norm and e_norm:
                    new_win = {"start": s_norm, "end": e_norm}
                    if new_win not in current_wins:
                        current_wins.append(new_win)
                        schedule_data["nurture_windows"] = current_wins
                        save_json(SCHEDULE_FILE, schedule_data)
                        st.success(f"Thêm khung: {s_norm}-{e_norm}")
                        time.sleep(0.5); st.rerun()
                else: st.error("Sai định dạng giờ!")

            if current_wins:
                st.write("Khung giờ:")
                for i, w in enumerate(current_wins):
                    c_txt, c_del = st.columns([4, 1])
                    c_txt.code(f"{w['start']} - {w['end']}")
                    if c_del.button("❌", key=f"del_w_{i}"):
                        current_wins.pop(i)
                        schedule_data["nurture_windows"] = current_wins
                        save_json(SCHEDULE_FILE, schedule_data)
                        st.rerun()
            else: st.caption("Chưa đặt giờ nuôi.")

    st.markdown("---")

    # --- KHU VỰC 3: ACTION BAR ---
    cnt_acc = sum(1 for a in acc_list if a.get("active"))
    cnt_chn = sum(1 for c in chn_list if c.get("active"))

    c1, c2, c3 = st.columns([1,1,2])
    c1.metric("Nick chạy", cnt_acc)
    c2.metric("Nguồn clone", cnt_chn)

    with c3:
        upload_limit = st.number_input("Số video mỗi Nick:", min_value=1, max_value=20, value=3)
        st.write(""); st.write("")
        if st.button("🚀 KHỞI ĐỘNG HỆ THỐNG", type="primary", width="stretch", disabled=(cnt_acc==0 or cnt_chn==0)):
            session_conf = {"upload_limit": upload_limit}
            save_json(SESSION_CONFIG_FILE, session_conf) # [FIX]

            script_path = os.path.join(PROJECT_ROOT, "scheduler_manager.py")
            if os.path.exists(script_path):
                st.toast(f"🚀 Khởi động Bot (Limit: {upload_limit}/nick)...")
                log_box = st.empty()
                full_log = ""
                try:
                    cmd = [sys.executable, "-u", script_path]
                    process = subprocess.Popen(cmd, cwd=PROJECT_ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
                    while True:
                        line = process.stdout.readline()
                        if line:
                            full_log += line
                            log_box.code("\n".join(full_log.splitlines()[-15:]), language="bash")
                        if not line and process.poll() is not None: break
                    st.success("Bot đã dừng.")
                except Exception as e: st.error(f"Lỗi: {e}")
            else: st.error("Thiếu file scheduler_manager.py")