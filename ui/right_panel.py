import streamlit as st
import time
import os
from config.settings import UPLOAD_TEMP_DIR, VIDEO_RESOLUTIONS, FRAME_DIR, LOGO_DIR
from services.sheet_api import save_audio_link_to_sheet, get_data_from_sheet
from modules.image_editor import create_frame_with_text, create_ui_thumbnail
from modules.search_engine import search_images_on_web
from modules.video_maker import create_video_from_scraped_data
from modules.video_remix import create_video_from_source_video

# Hàm xóa file tạm an toàn
def cleanup_temp_file(file_path):
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            return True
    except Exception as e:
        print(f"Error cleaning up: {e}")
    return False

# Callback thêm ảnh
def add_image_to_queue(url_to_add):
    if 'scraped_images' not in st.session_state: st.session_state['scraped_images'] = []
    if url_to_add not in st.session_state['scraped_images']:
        st.session_state['scraped_images'].append(url_to_add)
        st.toast(f"✅ Đã thêm ảnh!")
    else: st.toast("⚠️ Ảnh này đã có rồi.")

def render_right_panel(sheet_url):

    # Lấy chế độ đã được detect từ Left Panel
    work_mode = st.session_state.get('work_mode', 'Remix_Manual')

    # [QUAN TRỌNG] Lấy Link Video gốc (Cột H) từ Session
    original_video_url = st.session_state.get('original_video_url', '')

    # Tạo Key động cho Uploader
    curr_row = st.session_state.get('current_sheet_row', 'unknown')
    unique_uploader_key = f"vid_uploader_{work_mode}_{curr_row}"

    # Biến lưu lựa chọn kiểu Remix (Mặc định)
    remix_type_selection = "Nhiều thoại"

    # ==================================================
    # PHẦN 1: GIAO DIỆN QUẢN LÝ MEDIA
    # ==================================================

    # --- MODE 1: BÀI BÁO (Article) ---
    if work_mode == "Article":
        st.subheader("3. Quản lý Ảnh (Chế độ Báo)")

        # Xử lý dữ liệu Cột G (Combined Hints)
        raw_source = st.session_state.get('combined_hints') or st.session_state.get('sheet_image_prompts')

        prompts = []
        if raw_source:
            if isinstance(raw_source, list):
                for item in raw_source:
                    sub_lines = str(item).splitlines()
                    prompts.extend([x.strip() for x in sub_lines if x.strip()])
            elif isinstance(raw_source, str):
                prompts = [x.strip() for x in raw_source.splitlines() if x.strip()]

        if prompts:
            with st.expander(f"🔍 Tìm ảnh từ {len(prompts)} Gợi ý (Cột G)", expanded=True):
                st.write(f"**Danh sách từ khóa ({len(prompts)}):**")
                for p in prompts:
                    st.markdown(f"- `{p}`")

                max_imgs = st.slider("Số ảnh tìm mỗi từ khóa:", 1, 5, 2)

                if st.button("🚀 Tìm kiếm tất cả", width="stretch"):
                    st.session_state['search_results_preview'] = []
                    prog_bar = st.progress(0)
                    for i, k in enumerate(prompts):
                        prog_bar.progress((i + 1) / len(prompts))
                        res = search_images_on_web(k, max_imgs)
                        if res: st.session_state['search_results_preview'].extend(res)
                    prog_bar.empty()

                preview = st.session_state.get('search_results_preview', [])
                if preview:
                    st.caption(f"Tìm thấy {len(preview)} ảnh:")
                    cols = st.columns(3)
                    for idx, url in enumerate(preview):
                        with cols[idx % 3]:
                            try:
                                st.image(url, width="stretch")
                                st.button("➕", key=f"add_{idx}", on_click=add_image_to_queue, args=(url,))
                            except: pass

                    if st.button("➕ Thêm TẤT CẢ vào hàng đợi", width="stretch"):
                        count = 0
                        for url in preview:
                            if url not in st.session_state['scraped_images']:
                                st.session_state['scraped_images'].append(url); count+=1
                        st.toast(f"Đã thêm {count} ảnh"); st.rerun()
        else:
            st.info("ℹ️ Không tìm thấy từ khóa hình ảnh (Cột G) hoặc ô trống.")

        st.divider()

        # Upload ảnh thủ công
        ik = f"img_{st.session_state['img_key']}"
        up = st.file_uploader("➕ Tải ảnh lên:", accept_multiple_files=True, type=['jpg','png','jpeg'], key=ik)
        if up:
            for u in up:
                p = os.path.join(UPLOAD_TEMP_DIR, u.name)
                with open(p, "wb") as f: f.write(u.getbuffer())
                if p not in st.session_state['scraped_images']: st.session_state['scraped_images'].append(p)
            st.session_state['img_key']+=1; st.rerun()

        with st.expander("📝 Sắp xếp / Xóa ảnh đã chọn", expanded=False):
            curr = st.session_state.get('scraped_images', [])
            txt = "\n".join(curr)
            new_txt = st.text_area("List ảnh (Sửa đường dẫn để xóa):", value=txt, height=150)
            if new_txt != txt:
                st.session_state['scraped_images'] = [l.strip() for l in new_txt.split('\n') if l.strip()]
                st.rerun()

        curr = st.session_state.get('scraped_images', [])
        if curr:
            st.caption(f"✅ Đang có {len(curr)} ảnh sẵn sàng tạo video.")
            cols = st.columns(4)
            for idx, p in enumerate(curr):
                with cols[idx%4]:
                    th = create_ui_thumbnail(p, idx+1)
                    if th: st.image(th, width="stretch")
        else: st.warning("Danh sách ảnh đang trống.")

    # --- MODE 2: CLONE CÓ TƯ LIỆU (Remix_Source) ---
    elif work_mode == "Remix_Source":
        st.subheader("3. Video Nền (Tự động từ Cột H)")

        # [UPDATE] Hiển thị Link Cột H thay vì nút Upload
        if original_video_url:
            st.success(f"🔗 **Đã lấy Link gốc (Cột H):**")
            st.caption(f"{original_video_url}")
            st.info("ℹ️ Hệ thống sẽ tự động tải video này về xử lý.")
        else:
            st.error("⚠️ Không tìm thấy link Video gốc ở Cột H!")
            st.caption("👉 Vui lòng điền link video vào Cột H trên Google Sheet và bấm Load lại.")

        st.markdown("🎛️ **Chọn kiểu dựng:**")
        remix_type_selection = st.radio(
            "Loại kịch bản:", ["Nhiều thoại", "Ít thoại"],
            horizontal=True, label_visibility="collapsed", key="remix_source_type"
        )
        if remix_type_selection == "Nhiều thoại": st.caption("ℹ️ **Nhiều thoại:** Ghép Audio -> Loop Video.")
        else: st.caption("ℹ️ **Ít thoại:** Intro (Title Audio) + Full Video gốc.")
        st.write("---")

    # --- MODE 3: CLONE KHÔNG TƯ LIỆU (Remix_Manual) ---
    else:
        st.subheader("3. Video Nền (Không Tư liệu)")
        st.warning("⚠️ Cột A là Text/Trống -> Chế độ thủ công.")

        remix_type_selection = "Nhiều thoại"

        # Nút Upload Video (Chỉ hiện ở chế độ Manual)
        uploaded_video = st.file_uploader("📤 Upload Video Nền (Bắt buộc):", type=['mp4', 'mov', 'avi'], key=unique_uploader_key)

        if uploaded_video:
            if not os.path.exists(UPLOAD_TEMP_DIR): os.makedirs(UPLOAD_TEMP_DIR)
            temp_vid_path = os.path.join(UPLOAD_TEMP_DIR, "uploaded_source_video.mp4")
            with open(temp_vid_path, "wb") as f: f.write(uploaded_video.getbuffer())
            st.success("✅ Đã nhận video upload!")
            st.session_state['local_video_path'] = temp_vid_path
        else:
            if 'local_video_path' in st.session_state: del st.session_state['local_video_path']
            st.error("Chưa có Video nền!")

    st.divider()

    # ==================================================
    # PHẦN 2: AUDIO PLAYER
    # ==================================================
    if st.session_state.get('last_result'):
        res = st.session_state['last_result']
        audio_url = res.get('audio_link')
        if audio_url:
            with st.container(border=True):
                st.caption(f"🔊 Voice Kịch Bản (Content): {'Sheet' if res.get('is_existing') else 'Mới tạo'}")
                try: st.audio(audio_url)
                except: pass

                row = res.get('row')
                is_new = not res.get('is_existing')
                if is_new:
                    if st.button("💾 Lưu Voice Content", key="save_content_btn", width="stretch"):
                        save_audio_link_to_sheet(sheet_url, row, audio_url)
                        st.session_state['last_result']['is_existing']=True
                        st.toast("Đã lưu!"); time.sleep(1); st.rerun()

    if st.session_state.get('last_title_result'):
        res_t = st.session_state['last_title_result']
        if res_t.get('audio_link'):
            with st.container(border=True):
                st.caption("🔊 Voice Tiêu Đề (Title)")
                try: st.audio(res_t['audio_link'])
                except: pass

    st.divider()

    # ==================================================
    # PHẦN 3: RENDER VIDEO
    # ==================================================
    st.subheader("🎬 Xuất Video")

    with st.expander("🎨 Cấu hình Text & Logo", expanded=True):
        col_b_data = st.session_state.get('article_title', '')
        if 'prev_loaded_title' not in st.session_state: st.session_state['prev_loaded_title'] = None
        if col_b_data != st.session_state['prev_loaded_title']:
            st.session_state['ui_frame_title'] = col_b_data
            st.session_state['prev_loaded_title'] = col_b_data

        ut = st.text_input("Tiêu đề Video (Dữ liệu Cột B):", key="ui_frame_title")
        if not ut: st.caption("ℹ️ Hãy Load Data để lấy tiêu đề.")

        cl = None
        if os.path.exists(LOGO_DIR):
            for f in os.listdir(LOGO_DIR):
                if f.endswith(('.png','.jpg')): cl=os.path.join(LOGO_DIR, f); break
        c1, c2 = st.columns([1,2])
        with c1:
            if cl: st.image(cl, width=80)
        with c2:
            lk = f"logo_{st.session_state['logo_key']}"
            upl = st.file_uploader("Upload Logo", type=['png'], key=lk)
            if upl:
                if os.path.exists(LOGO_DIR):
                    for f in os.listdir(LOGO_DIR): os.remove(os.path.join(LOGO_DIR,f))
                with open(os.path.join(LOGO_DIR, upl.name), "wb") as f: f.write(upl.getbuffer())
                st.session_state['logo_key']+=1; st.rerun()

    res_sel = st.selectbox("Độ phân giải:", list(VIDEO_RESOLUTIONS.keys()))

    if st.button("🚀 XUẤT VIDEO NGAY", type="primary", width="stretch"):

        # Tìm Frame trong folder (Chế độ thủ công hiện tại chỉ lấy 1 frame làm chung)
        cover = None
        for e in ['png','jpg']:
            fp=os.path.join(FRAME_DIR, f"fr.{e}")
            if os.path.exists(fp): cover=fp; break

        # Tìm Logo
        logo = None
        if os.path.exists(LOGO_DIR):
            for f in os.listdir(LOGO_DIR):
                if f.endswith(('.png','.jpg')): logo=os.path.join(LOGO_DIR, f); break

        # Tạo Text Layer
        txt_l = None
        if ut:
            with st.spinner("🎨 Đang tạo Text Layer..."):
                ref = None
                if work_mode == "Article" and len(st.session_state.get('scraped_images', [])) > 0:
                    ref = st.session_state['scraped_images'][0]
                elif cover: ref = cover
                if ref: txt_l = create_frame_with_text(ref, ut)
                else: st.warning("⚠️ Không tìm thấy ảnh mẫu (hoặc Frame) để tạo Text.")

        try:
            # 1. Lấy thông tin Audio
            a_url = None
            if st.session_state.get('last_result'):
                a_url = st.session_state['last_result'].get('audio_link')

            title_audio_url = None
            if st.session_state.get('last_title_result'):
                title_audio_url = st.session_state['last_title_result'].get('audio_link')

            # 2. Kiểm tra điều kiện Audio
            if work_mode == "Remix_Source" and remix_type_selection == "Ít thoại":
                if not title_audio_url:
                    st.error("❌ Lỗi: Chế độ 'Ít thoại' bắt buộc phải có Voice Title (Cột D).")
                    st.stop()
            else:
                if not a_url:
                    st.error("❌ Lỗi: Chưa có Voice Kịch bản (Content Audio)!")
                    st.stop()

            # --- TRƯỜNG HỢP: BÀI BÁO (Article) ---
            if work_mode == "Article":
                imgs = st.session_state.get('scraped_images', [])
                if imgs:
                    # [FIXED] Gọi hàm với Keywword Arguments để tránh lỗi nhầm vị trí
                    out = create_video_from_scraped_data(
                        audio_url=a_url,
                        image_list=imgs,
                        resolution_tuple=VIDEO_RESOLUTIONS[res_sel],
                        output_filename=f"vid_img_{int(time.time())}.mp4",

                        # Sử dụng cover chung cho cả 2 loại frame trong chế độ thủ công
                        title_frame_path=cover,
                        content_frame_path=cover,

                        text_overlay_path=txt_l,
                        logo_path=logo,
                        title_audio_url=title_audio_url
                    )
                    st.success(f"✅ Xong! Lưu tại: {out}")
                    st.video(out)
                    with open(out, "rb") as f: st.download_button("⬇️ Tải Video", f, out, "video/mp4")

                    # Dọn dẹp Text Layer
                    if txt_l and os.path.exists(txt_l): os.remove(txt_l)
                else: st.error("Cần ít nhất 1 ảnh.")

            # --- TRƯỜNG HỢP: REMIX (Source hoặc Manual) ---
            else:
                target_vid = None

                if work_mode == "Remix_Source":
                    if original_video_url:
                        target_vid = original_video_url
                    else:
                        st.error("❌ Không tìm thấy Link Video gốc (Cột H).")
                        st.stop()
                else:
                    if 'local_video_path' in st.session_state and os.path.exists(st.session_state['local_video_path']):
                        target_vid = st.session_state['local_video_path']

                if target_vid:
                    # Gọi hàm render Remix
                    out = create_video_from_source_video(
                        audio_url=a_url,
                        source_video_url=target_vid,
                        resolution_tuple=VIDEO_RESOLUTIONS[res_sel],
                        output_filename=f"vid_remix_{int(time.time())}.mp4",
                        cover_image_path=cover, # Lưu ý: Hàm remix này có thể chưa tách 2 frame, nếu cần báo mình sửa nốt
                        text_overlay_path=txt_l,
                        logo_path=logo,
                        remix_type=remix_type_selection,
                        title_audio_url=title_audio_url
                    )
                    st.success(f"✅ Xong! Lưu tại: {out}")
                    st.video(out)
                    with open(out, "rb") as f: st.download_button("⬇️ Tải Video", f, out, "video/mp4")

                    if txt_l and os.path.exists(txt_l): os.remove(txt_l)
                    if work_mode != "Remix_Source":
                        if cleanup_temp_file(target_vid):
                            st.toast("🗑️ Đã xóa file gốc tạm thời.")
                            if 'local_video_path' in st.session_state:
                                del st.session_state['local_video_path']
                else:
                    st.error("❌ Chưa có Video nền!")

        except Exception as e: st.error(f"Lỗi Render: {e}")