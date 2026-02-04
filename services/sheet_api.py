import requests
import json

# ==============================================================================
# 1. HÀM ĐỌC DỮ LIỆU (READ) - [ĐÃ SỬA: BỎ XUỐNG DÒNG]
# ==============================================================================
def get_data_from_sheet(script_url, row_number=None):
    if not script_url:
        return None

    # Chuẩn bị payload
    payload = {"action": "read"}
    if row_number:
        payload["row"] = int(row_number)

    try:
        # Tăng timeout lên 30s để tránh bị ngắt kết nối sớm nếu mạng chậm
        res = requests.post(script_url, json=payload, timeout=30)

        # Kiểm tra nếu server trả về lỗi (không phải JSON)
        if res.status_code != 200:
            print(f"❌ Lỗi kết nối Sheet: {res.status_code}")
            return None

        data = res.json()

        if data.get("status") == "success":
            # --- XỬ LÝ TEXT: BỎ XUỐNG DÒNG ---
            raw_title = data.get("title_text", "")
            # Thay thế xuống dòng bằng khoảng trắng và cắt khoảng trắng thừa 2 đầu
            clean_title = raw_title.replace("\n", " ").strip() if raw_title else ""

            raw_content = data.get("content_text", "")
            # Thay thế xuống dòng bằng khoảng trắng
            clean_content = raw_content.replace("\n", " ").strip() if raw_content else ""
            # ---------------------------------

            return (
                data.get("url", "").strip(),
                clean_title,
                clean_content,
                data.get("row"),
                data.get("existing_content_audio", ""),
                data.get("existing_title_audio", ""),
                data.get("image_prompts", []),
                data.get("original_video_url", ""),
                data.get("title_tiktok", ""),
                "OK"
            )
        else:
            print(f"⚠️ Sheet báo lỗi: {data.get('message')}")
            return None

    except Exception as e:
        print(f"❌ Lỗi Exception Sheet: {e}")
        return None

# ==============================================================================
# 2. HÀM CẬP NHẬT THÔNG TIN (UPDATE)
# ==============================================================================
def update_tiktok_info(script_url, row, file_path=None, link_tiktok=None, title_tiktok=None):
    """
    Gửi thông tin cập nhật (Link video, File path...) lên Sheet - GIỮ NGUYÊN
    """
    try:
        payload = {
            "action": "update_tiktok_info",
            "row": row
        }
        if file_path: payload["file_path"] = str(file_path)
        if link_tiktok: payload["link_tiktok"] = str(link_tiktok)
        if title_tiktok: payload["title_tiktok"] = str(title_tiktok)

        requests.post(script_url, json=payload, timeout=20)
        return True
    except Exception as e:
        print(f"❌ Lỗi update info: {e}")
        return False

def update_status_to_sheet(sheet_url, row_idx, content):
    """
    Wrapper đơn giản: Cập nhật link TikTok vào cột Video - GIỮ NGUYÊN
    """
    print(f"📝 Đang lưu link vào dòng {row_idx}...")
    return update_tiktok_info(sheet_url, row_idx, link_tiktok=content)

# ------------------------------------------------------------------------------
# 2 HÀM NÀY ĐỂ KHỚP VỚI APPS SCRIPT "update_voice"
# ------------------------------------------------------------------------------
def save_audio_link_to_sheet(script_url, row, audio_link):
    """Lưu Voice Nội dung (Cột F)"""
    try:
        payload = {
            "action": "update_voice",
            "content_voice": str(audio_link),
            "row": int(row)
        }
        requests.post(script_url, json=payload, timeout=20)
        return True
    except: return False

def save_title_audio_to_sheet(script_url, row, audio_link):
    """Lưu Voice Tiêu đề (Cột D)"""
    try:
        payload = {
            "action": "update_voice",
            "title_voice": str(audio_link),
            "row": int(row)
        }
        requests.post(script_url, json=payload, timeout=20)
        return True
    except: return False
# ------------------------------------------------------------------------------

# ==============================================================================
# 3. HÀM LẤY DÒNG CUỐI (QUAN TRỌNG - FIX TREO) - GIỮ NGUYÊN
# ==============================================================================
def get_last_row_index(sheet_url):
    """
    Hàm này lấy dòng cuối cùng có dữ liệu.
    Đã thêm Timeout ngắn (5s) để không bị treo nếu mạng lag.
    """
    try:
        # Gửi row="" để Apps Script hiểu là muốn lấy thông tin chung (hoặc dòng cuối)
        payload = {"action": "read", "row": ""}

        # Timeout 5s: Nếu quá 5s không trả lời thì bỏ qua để Bot chạy tiếp
        response = requests.post(sheet_url, json=payload, timeout=10)

        data = response.json()

        if data.get("status") == "success":
            # Nếu script trả về row, dùng nó. Nếu không, mặc định trả về 0
            return int(data.get("row", 0))

        return 0

    except requests.exceptions.Timeout:
        print("⚠️ Lấy dòng cuối bị Timeout (quá 5s) -> Bỏ qua.")
        return 0
    except Exception as e:
        print(f"❌ Lỗi lấy dòng cuối: {e}")
        return 0

