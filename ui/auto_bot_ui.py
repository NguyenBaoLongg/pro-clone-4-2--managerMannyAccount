import streamlit as st
import json
import os
import time
import subprocess
import sys
import pandas as pd
from datetime import datetime

# ================= CẤU HÌNH PATH =================
CURRENT_FILE = os.path.abspath(__file__)
UI_DIR = os.path.dirname(CURRENT_FILE)
PROJECT_ROOT = os.path.dirname(UI_DIR)
CONFIG_DIR = os.path.join(PROJECT_ROOT, "config")
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")

# Đảm bảo folder frame tồn tại
FRAME_DIR = os.path.join(ASSETS_DIR, "frame")
if not os.path.exists(FRAME_DIR): os.makedirs(FRAME_DIR)

# Các file config
TRACKING_FILE = os.path.join(CONFIG_DIR, "channels_tracking.json")
ACCOUNTS_FILE = os.path.join(CONFIG_DIR, "tiktok_accounts.json")
RENDER_CONFIG_FILE = os.path.join(CONFIG_DIR, "render_config.json")
USER_SETTINGS_FILE = os.path.join(PROJECT_ROOT, "user_settings.json")
SCHEDULE_FILE = os.path.join(CONFIG_DIR, "schedule_config.json")

# --- HELPER FUNCTIONS ---
def load_json(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f: return json.load(f)
        except: return {}
    return {}

def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def save_frame_image(uploaded_file):
    if uploaded_file:
        try:
            file_path = os.path.join(FRAME_DIR, uploaded_file.name)
            with open(file_path, "wb") as f: f.write(uploaded_file.getbuffer())
            return uploaded_file.name
        except Exception as e:
            st.error(f"Lỗi lưu ảnh: {e}")
    return None

def normalize_time_input(time_str):
    """Chuyển đổi giờ nhập bất kỳ thành HH:MM"""
    try:
        t = time_str.strip()
        dt = datetime.strptime(t, "%H:%M")
        return dt.strftime("%H:%M")
    except:
        return None

# ==============================================================================
# MÀN HÌNH 1: DASHBOARD
# ==============================================================================
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
            with open(os.path.join(CONFIG_DIR, "session_config.json"), "w") as f:
                json.dump(session_conf, f)

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

# ==============================================================================
# MÀN HÌNH 2: QUẢN LÝ TÀI KHOẢN (GIỮ NGUYÊN)
# ==============================================================================
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

# ==============================================================================
# MÀN HÌNH 3: QUẢN LÝ KÊNH CLONE (ĐƠN GIẢN HÓA: CHỈ CẤU HÌNH KÊNH)
# ==============================================================================
def render_channel_manager():
    st.markdown("## 📺 Quản lý Kênh Nguồn (Clone)")
    st.caption("Cấu hình cách Edit cho từng Kênh nguồn (Áp dụng tự động cho mọi nick).")

    tracking_data = load_json(TRACKING_FILE)
    chn_list = tracking_data if isinstance(tracking_data, list) else tracking_data.get("channels", [])

    render_data = load_json(RENDER_CONFIG_FILE)
    render_list = render_data if isinstance(render_data, list) else []

    # --- A. FORM THÊM MỚI ---
    with st.expander("➕ Thêm Cấu hình Kênh Mới", expanded=False):
        with st.form("add_channel_form_v4"):
            st.info("Nhập link kênh. Hệ thống sẽ tự động dùng cấu hình này khi clone từ kênh này.")

            c_url, c_lim = st.columns([3, 1])
            new_url = c_url.text_input("🔗 Link Kênh TikTok Nguồn:")
            new_limit = c_lim.number_input("Limit (số video quét):", 1, 50, 5)

            st.divider()

            t1, t2, t3, t4 = st.tabs(["Intro", "Content", "Text", "Assets"])
            with t1:
                col_a, col_b = st.columns(2)
                t_start = col_a.number_input("Intro Start", 0.0, 60.0, 2.0)
                t_end = col_a.number_input("Intro End", 0.0, 60.0, 5.0)
                t_zoom = col_b.number_input("Intro Zoom", 1.0, 3.0, 1.3)
                t_off = col_b.text_input("Intro Offset Y", "-150")
            with t2:
                col_c, col_d = st.columns(2)
                c_start = col_c.number_input("Content Start", 0.0, 300.0, 8.0)
                c_end = col_c.text_input("Content End", "auto")
                c_zoom = col_d.number_input("Content Zoom", 1.0, 3.0, 1.3)
                c_off = col_d.text_input("Content Offset Y", "-400")
            with t3:
                f_name = st.text_input("Font (.ttf)", "Inter_18pt-Bold.ttf")
                f_size = st.number_input("Size", 10, 100, 50)
                c_intro = st.color_picker("Color Intro", "#b5045b")
                c_cont = st.color_picker("Color Content", "#FFFFFF")
            with t4:
                c7, c8 = st.columns(2)
                with c7:
                    st.write("🖼️ Intro Frame")
                    up_fri = st.file_uploader("Upload Intro", key="new_up_fri")
                    val_fri = save_frame_image(up_fri) if up_fri else "fr.png"
                    fr_i = st.text_input("Tên file Intro", val_fri)
                with c8:
                    st.write("🖼️ Content Frame")
                    up_frc = st.file_uploader("Upload Content", key="new_up_frc")
                    val_frc = save_frame_image(up_frc) if up_frc else "fr 1.png"
                    fr_c = st.text_input("Tên file Content", val_frc)
                lg_f = st.text_input("Logo (.png)", "")
                lg_w = st.number_input("Logo Width", 50, 300, 150)

            if st.form_submit_button("💾 LƯU CẤU HÌNH", type="primary"):
                if "http" in new_url:
                    clean_url = new_url.strip()

                    # 1. Update Tracking
                    if not any(c['channel_url'] == clean_url for c in chn_list):
                        chn_list.append({"channel_url": clean_url, "last_video_url": "", "scan_limit": new_limit, "active": True})
                        save_json(TRACKING_FILE, {"channels": chn_list})

                    # 2. Tạo Object Config (Không gán tiktok_id -> Generic)
                    new_cfg = {
                        "channel_url": clean_url,
                        # "tiktok_id": None, # KHÔNG GÁN ID CỤ THỂ
                        "title_settings": {"source_start": t_start, "source_end": t_end, "zoom_factor": t_zoom, "manual_x_offset": "center", "manual_y_offset": int(t_off) if t_off.lstrip('-').isdigit() else t_off},
                        "content_settings": {"source_start": c_start, "source_end": float(c_end) if c_end.replace('.','',1).isdigit() else "auto", "zoom_factor": c_zoom, "manual_x_offset": 0, "manual_y_offset": int(c_off) if c_off.lstrip('-').isdigit() else c_off},
                        "text_overlay_settings": {"font_filename": f_name, "font_size": f_size, "text_color": c_intro, "box_width_percentage": 0.65, "box_y_start": 0.7},
                        "text_content_settings": {"font_filename": f_name, "font_size": int(f_size*0.7), "text_color": c_cont, "box_width_percentage": 0.85, "box_y_start": 0.15},
                        "assets": {"title_frame_filename": fr_i, "content_frame_filename": fr_c, "font_filename": f_name, "logo_filename": lg_f, "logo_width": lg_w}
                    }

                    # 3. Upsert
                    found = False
                    for idx, r in enumerate(render_list):
                        # Chỉ check URL vì đây là config chung
                        if r.get("channel_url") == clean_url:
                            render_list[idx] = new_cfg; found = True; break

                    if not found: render_list.append(new_cfg)

                    save_json(RENDER_CONFIG_FILE, render_list)
                    st.success(f"✅ Đã lưu cấu hình chung cho kênh: {clean_url}")
                    time.sleep(1); st.rerun()
                else: st.error("Link lỗi.")

    # --- B. DANH SÁCH ---
    st.divider()
    st.subheader(f"📋 Danh sách Cấu hình Kênh ({len(render_list)})")

    if not render_list: st.info("Chưa có cấu hình nào.")

    for i, cfg in enumerate(render_list):
        url = cfg.get('channel_url', 'Unknown')
        label = f"⚙️ {url}" # Không còn hiển thị Nick

        ts = cfg.get("title_settings", {})
        cs = cfg.get("content_settings", {})
        tx = cfg.get("text_overlay_settings", {})
        tx2 = cfg.get("text_content_settings", {})
        ast = cfg.get("assets", {})

        with st.expander(label):
            st.caption(f"Cấu hình này sẽ áp dụng cho bất kỳ Nick nào lấy video từ {url}")

            et1, et2, et3, et4 = st.tabs(["Intro", "Content", "Text", "Assets"])
            with et1:
                ec1, ec2 = st.columns(2)
                e_t_st = ec1.number_input(f"Start ##{i}", 0.0, 60.0, float(ts.get("source_start", 2.0)))
                e_t_en = ec1.number_input(f"End ##{i}", 0.0, 60.0, float(ts.get("source_end", 5.0)))
                e_t_zm = ec2.number_input(f"Zoom ##{i}", 1.0, 3.0, float(ts.get("zoom_factor", 1.3)))
                e_t_off = ec2.text_input(f"Off Y ##{i}", str(ts.get("manual_y_offset", -150)))
            with et2:
                ec3, ec4 = st.columns(2)
                e_c_st = ec3.number_input(f"C Start ##{i}", 0.0, 300.0, float(cs.get("source_start", 8.0)))
                e_c_en = ec3.text_input(f"C End ##{i}", str(cs.get("source_end", "auto")))
                e_c_zm = ec4.number_input(f"C Zoom ##{i}", 1.0, 3.0, float(cs.get("zoom_factor", 1.3)))
                e_c_off = ec4.text_input(f"C Off Y ##{i}", str(cs.get("manual_y_offset", -400)))
            with et3:
                e_font = st.text_input(f"Font ##{i}", str(tx.get("font_filename", "Inter_18pt-Bold.ttf")))
                e_size = st.number_input(f"Size ##{i}", 10, 100, int(tx.get("font_size", 50)))
                e_col1 = st.color_picker(f"Col Intro ##{i}", str(tx.get("text_color", "#b5045b")))
                e_col2 = st.color_picker(f"Col Content ##{i}", str(tx2.get("text_color", "#FFFFFF")))
            with et4:
                ac1, ac2 = st.columns(2)
                with ac1:
                    st.markdown("**🖼️ Intro Frame**")
                    cur_fri = str(ast.get("title_frame_filename", "fr.png"))
                    path_fri = os.path.join(FRAME_DIR, cur_fri)
                    if os.path.exists(path_fri): st.image(path_fri, width=100)
                    up_fri_edit = st.file_uploader("Đổi Intro:", key=f"up_fri_{i}")
                    if up_fri_edit: cur_fri = save_frame_image(up_fri_edit); st.success("OK!")
                    e_fri = st.text_input(f"File Intro ##{i}", cur_fri)
                with ac2:
                    st.markdown("**🖼️ Content Frame**")
                    cur_frc = str(ast.get("content_frame_filename", "fr 1.png"))
                    path_frc = os.path.join(FRAME_DIR, cur_frc)
                    if os.path.exists(path_frc): st.image(path_frc, width=100)
                    up_frc_edit = st.file_uploader("Đổi Content:", key=f"up_frc_{i}")
                    if up_frc_edit: cur_frc = save_frame_image(up_frc_edit); st.success("OK!")
                    e_frc = st.text_input(f"File Content ##{i}", cur_frc)
                e_lg = st.text_input(f"Logo ##{i}", str(ast.get("logo_filename", "")))
                e_lgw = st.number_input(f"Logo W ##{i}", 50, 300, int(ast.get("logo_width", 150)))

            st.write("")
            col_save, col_del = st.columns([1, 1])
            if col_save.button("💾 CẬP NHẬT", key=f"btn_save_{i}"):
                # Update list
                render_list[i]["title_settings"] = {"source_start": e_t_st, "source_end": e_t_en, "zoom_factor": e_t_zm, "manual_x_offset": "center", "manual_y_offset": int(e_t_off) if e_t_off.lstrip('-').isdigit() else e_t_off}
                render_list[i]["content_settings"] = {"source_start": e_c_st, "source_end": float(e_c_en) if e_c_en.replace('.','',1).isdigit() else "auto", "zoom_factor": e_c_zm, "manual_x_offset": 0, "manual_y_offset": int(e_c_off) if e_c_off.lstrip('-').isdigit() else e_c_off}
                render_list[i]["text_overlay_settings"] = {"font_filename": e_font, "font_size": e_size, "text_color": e_col1, "box_width_percentage": 0.65, "box_y_start": 0.7}
                render_list[i]["text_content_settings"] = {"font_filename": e_font, "font_size": int(e_size*0.7), "text_color": e_col2, "box_width_percentage": 0.85, "box_y_start": 0.15}
                render_list[i]["assets"] = {"title_frame_filename": e_fri, "content_frame_filename": e_frc, "font_filename": e_font, "logo_filename": e_lg, "logo_width": e_lgw}

                save_json(RENDER_CONFIG_FILE, render_list)
                st.toast("✅ Đã cập nhật!"); time.sleep(1); st.rerun()

            if col_del.button("🗑️ XÓA", key=f"btn_del_{i}", type="primary"):
                render_list.pop(i)
                save_json(RENDER_CONFIG_FILE, render_list)
                st.rerun()

# ================= MAIN ROUTER =================
def render_api_settings():
    st.markdown("## 🔑 Cấu hình API & Hệ thống")
    settings = load_json(USER_SETTINGS_FILE)
    with st.form("api_settings_form"):
        st.subheader("1. Hệ thống AI Studio")
        ai_url = st.text_input("AI Studio URL:", value=settings.get("ai_studio_url", ""))
        st.subheader("2. Text-to-Speech (TTS)")
        api_key = st.text_input("API Key (TTS Provider):", value=settings.get("api_key", ""), type="password")
        voice_id = st.text_input("Voice ID Mặc định:", value=settings.get("voice_id", "vi_female_kieunhi_mn"))
        st.subheader("3. Google Sheet (Database)")
        sheet_url = st.text_input("Apps Script URL:", value=settings.get("sheet_url", ""))
        if st.form_submit_button("💾 LƯU CẤU HÌNH", type="primary"):
            new_data = {"api_key": api_key.strip(), "sheet_url": sheet_url.strip(), "voice_id": voice_id.strip(), "ai_studio_url": ai_url.strip()}
            save_json(USER_SETTINGS_FILE, {**settings, **new_data})
            st.success("✅ Đã lưu cấu hình!")

def render_auto_bot_page(page_name="Dashboard"):
    if "Dashboard" in page_name: render_dashboard()
    elif "Quản lý Tài khoản" in page_name: render_account_manager()
    elif "Quản lý Kênh Clone" in page_name: render_channel_manager()
    elif "Cấu hình API" in page_name: render_api_settings()
    else: render_dashboard()