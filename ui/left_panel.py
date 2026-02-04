import streamlit as st
import time
# Đảm bảo bạn import đúng file chứa hàm get_data_from_sheet mới sửa
from services.sheet_api import get_data_from_sheet, save_title_audio_to_sheet
from services.tts_api import generate_voice, check_request_status
from modules.scraper import scrape_article_content
from config.settings import save_user_settings

def render_left_panel(api_key, sheet_url, voice_id):
    # ==========================================
    # PHẦN 1: LOAD DỮ LIỆU & AUTO DETECT
    # ==========================================
    st.subheader("1. Dữ liệu nguồn (Input)")
    c1, c2 = st.columns([3, 2])
    with c1: row_in = st.text_input("Row Number:", placeholder="Để trống = Auto")
    with c2:
        st.write(""); st.write("")
        load_btn = st.button("📥 Load & Detect", width="stretch")

    if load_btn:
        if not sheet_url: st.error("Thiếu URL Sheet!")
        else:
            with st.spinner("Đang tải & Phân tích dữ liệu..."):
                try:
                    # [UPDATE QUAN TRỌNG] Hứng đủ 10 biến (Thêm title_tiktok)
                    # Nếu file sheet_api chưa cập nhật trả về 10 biến, nó sẽ nhảy vào except
                    data_tuple = get_data_from_sheet(sheet_url, row_in)

                    if len(data_tuple) == 10:
                        url_res, title_text_b, content_text_c, real_row, exist_content_audio, exist_title_audio, prompts, original_video_url, title_tiktok, msg = data_tuple
                    elif len(data_tuple) == 9:
                        # Fallback cho trường hợp cũ (9 biến)
                        url_res, title_text_b, content_text_c, real_row, exist_content_audio, exist_title_audio, prompts, original_video_url, msg = data_tuple
                        title_tiktok = "" # Mặc định rỗng
                    else:
                        st.error(f"Lỗi API: Hàm trả về {len(data_tuple)} giá trị, nhưng cần 10.")
                        return

                except Exception as e:
                    st.error(f"Lỗi cấu trúc dữ liệu: {e}")
                    return

            if msg == "OK":
                st.session_state['current_sheet_row'] = real_row
                st.info(f"Đã load dòng: {real_row}")

                # [UPDATE] Lưu các biến quan trọng vào Session để dùng bên Right Panel
                st.session_state['original_video_url'] = original_video_url
                st.session_state['title_tiktok'] = title_tiktok # [QUAN TRỌNG] Lưu Caption TikTok

                # ========================================================
                # [LOGIC] NHẬN DIỆN CHẾ ĐỘ
                # ========================================================
                detected_mode = "Remix_Manual"
                data_col_a = str(url_res).strip().lower() if url_res else ""

                if "clone video có sẵn tư liệu" in data_col_a:
                    detected_mode = "Remix_Source"
                elif "clone video không có tư liệu" in data_col_a:
                    detected_mode = "Remix_Manual"
                elif "http" in data_col_a:
                    is_video_file = any(ext in data_col_a for ext in ['.mp4', '.mov', '.avi', 'drive.google.com'])
                    if is_video_file:
                        detected_mode = "Remix_Source"
                    else:
                        detected_mode = "Article"
                else:
                    detected_mode = "Remix_Manual"

                st.session_state['work_mode'] = detected_mode

                # --- XỬ LÝ TEXT & MEDIA ---
                final_title = title_text_b if title_text_b else ""
                final_content = content_text_c if content_text_c else ""

                st.session_state['scraped_images'] = []
                st.session_state['sheet_image_prompts'] = prompts
                st.session_state['combined_hints'] = prompts
                st.session_state['source_video_url'] = ""

                # Thông báo chế độ
                if detected_mode == "Article":
                    st.success("📰 Mode: BÀI BÁO (Link Báo)")
                    with st.spinner("Đang cào nội dung..."):
                        if "http" in data_col_a and not "clone" in data_col_a:
                            scraped_title, scraped_txt, imgs, s_msg = scrape_article_content(url_res)
                            if not final_title: final_title = scraped_title
                            if not final_content: final_content = scraped_txt if scraped_txt else content_text_c
                            if imgs: st.session_state['scraped_images'] = imgs
                        else:
                            st.info("Dùng dữ liệu có sẵn trên Sheet.")

                elif detected_mode == "Remix_Source":
                    st.success("🎥 Mode: CLONE CÓ TƯ LIỆU")
                    if original_video_url:
                        st.caption(f"Video gốc (Cột H): {original_video_url}")
                    else:
                        st.warning("⚠️ Chưa có link video gốc ở Cột H!")
                    if not final_title: final_title = "Video Remix Title"

                else:
                    st.warning("🛠️ Mode: CLONE KHÔNG TƯ LIỆU")
                    if not final_title and not "http" in data_col_a and url_res:
                        final_title = url_res

                # === CẬP NHẬT GIAO DIỆN ===
                st.session_state['input_title_voice'] = final_title
                st.session_state['main_text_area'] = final_content
                st.session_state['article_title'] = final_title

                # Check Voice cũ
                if exist_title_audio and len(exist_title_audio) > 5:
                    st.session_state['last_title_result'] = {"audio_link": exist_title_audio, "row": real_row}
                else:
                    if 'last_title_result' in st.session_state: del st.session_state['last_title_result']

                if exist_content_audio and len(exist_content_audio) > 5:
                    st.session_state['has_old_audio_on_sheet'] = True
                    st.session_state['last_result'] = {"audio_link": exist_content_audio, "row": real_row, "is_existing": True}
                else:
                    st.session_state['has_old_audio_on_sheet'] = False
                    if 'last_result' in st.session_state: del st.session_state['last_result']
            else: st.error(msg)

    st.divider()

    # ==========================================
    # PHẦN 2: KỊCH BẢN & GIỌNG ĐỌC
    # ==========================================
    st.subheader("2. Kịch bản & Giọng đọc")

    # --- A. TITLE VOICE ---
    st.markdown("##### 🅰️ Tiêu đề (Title) - Lấy Cột B, Lưu Cột D")
    title_in = st.text_area("Nhập Tiêu đề:", height=70, key="input_title_voice", label_visibility="collapsed", placeholder="Nhập tiêu đề...")

    tc1, tc2, tc3 = st.columns([1.5, 1.5, 2])
    with tc1: t_speed = st.slider("Tốc độ", 0.5, 2.0, 1.0, 0.1, key="spd_title")
    with tc2: t_pitch = st.slider("Cao độ", 0.5, 2.0, 1.0, 0.1, key="ptc_title")
    with tc3:
        st.write(""); st.write("")
        btn_gen_title = st.button("🔊 Tạo Voice Title", type="secondary", width="stretch")

    if btn_gen_title:
        save_user_settings(api_key, sheet_url, voice_id)
        with st.spinner('Creating Title...'):
            try:
                req_id = generate_voice(api_key, title_in, voice_id, t_speed, t_pitch)
                proc = True; r = 0; p = st.progress(0)
                while proc:
                    time.sleep(1); r+=1; p.progress(min(r*10, 90))
                    res = check_request_status(api_key, req_id)
                    if res and res.get("audio_link"):
                        st.session_state['last_title_result'] = {
                            "audio_link": res["audio_link"],
                            "row": st.session_state.get('current_sheet_row')
                        }
                        proc = False; p.progress(100)
                    elif r > 60: proc = False; st.error("Timeout")
            except Exception as e: st.error(f"Lỗi: {e}")

    # Player Title
    if st.session_state.get('last_title_result'):
        res_t = st.session_state['last_title_result']
        c_play, c_save = st.columns([3, 2])
        with c_play: st.audio(res_t['audio_link'])
        with c_save:
            row_t = res_t.get('row')
            if st.button(f"💾 Lưu Cột D", key="btn_save_title_voice", width="stretch"):
                saved = save_title_audio_to_sheet(sheet_url, row_t, res_t['audio_link'])
                if saved:
                    st.toast(f"✅ Đã lưu vào Cột D (Dòng {saved})!")
                    st.session_state['current_sheet_row'] = saved
                else: st.error("Lỗi lưu Sheet.")

    st.markdown("---")

    # --- B. CONTENT VOICE ---
    st.markdown("##### 🅱️ Nội dung chính (Content) - Lấy Cột C, Lưu Cột F")
    text_input = st.text_area("Nhập Nội dung:", height=200, key="main_text_area", label_visibility="collapsed", placeholder="Nhập nội dung...")

    cc1, cc2 = st.columns(2)
    with cc1: speed = st.slider("Tốc độ đọc", 0.5, 2.0, 1.0, 0.1, key="spd_content")
    with cc2: pitch = st.slider("Cao độ đọc", 0.5, 2.0, 1.0, 0.1, key="ptc_content")

    if st.button("▶️ Tạo Voice Kịch bản (Content)", type="primary", disabled=(not text_input), width="stretch"):
        save_user_settings(api_key, sheet_url, voice_id)
        with st.spinner('Creating Content...'):
            try:
                req_id = generate_voice(api_key, text_input, voice_id, speed, pitch)
                proc = True; p = st.progress(0); r = 0
                while proc:
                    time.sleep(2); r+=1; p.progress(min(r*5, 90))
                    res = check_request_status(api_key, req_id)
                    if res and res.get("audio_link"):
                        st.session_state['last_result'] = {
                            "audio_link": res["audio_link"],
                            "row": st.session_state.get('current_sheet_row'),
                            "imgs": st.session_state.get('scraped_images'),
                            "is_existing": False
                        }
                        proc = False; p.progress(100)
                    elif r > 60: proc = False; st.error("Timeout")
            except Exception as e: st.error(f"Lỗi: {e}")