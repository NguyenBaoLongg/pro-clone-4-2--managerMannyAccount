import os
import json
import requests
import yt_dlp
import shutil
import time  # [THÊM] Để tạo timestamp

# Xác định đường dẫn gốc dự án
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(MODULE_DIR)
RAPID_CONFIG_FILE = os.path.join(PROJECT_ROOT, "config", "rapid_api.json")

def load_rapid_config():
    """Hàm đọc cấu hình RapidAPI từ file JSON"""
    if not os.path.exists(RAPID_CONFIG_FILE):
        return {}
    try:
        with open(RAPID_CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

# --- PHẦN 1: CRAWLER (LẤY LINK VIDEO) ---

def get_videos_via_rapidapi(channel_url, limit=5):
    """Sử dụng RapidAPI quét danh sách video nếu yt-dlp thất bại"""
    config = load_rapid_config()
    # [FIX] Xử lý username kỹ hơn để tránh lỗi nếu URL có query params
    try:
        if "@" in channel_url:
            username = channel_url.split('@')[-1].split('?')[0].strip('/')
        else:
            username = channel_url.split('/')[-1].split('?')[0]
    except: return []

    headers = {
        "x-rapidapi-key": config.get("keys", [""])[0],
        "x-rapidapi-host": config.get("host", "")
    }

    video_links = []
    try:
        # Endpoint này thường thay đổi tùy gói API bạn mua, hãy đảm bảo endpoint đúng
        url = "https://tiktok-downloader-download-tiktok-videos-without-watermark.p.rapidapi.com/user/index"
        response = requests.get(url, headers=headers, params={"username": username}, timeout=20)
        data = response.json()

        # Cấu trúc data phụ thuộc vào API cụ thể, code dưới là ví dụ phổ biến
        if isinstance(data, dict):
            # Một số API trả về data bên trong key 'data', một số trả thẳng list
            items = data.get("data", {}).get("videos", []) if "data" in data else data.get("videos", [])

            for item in items[:limit]:
                vid_id = item.get("video_id")
                if vid_id:
                    video_links.append(f"https://www.tiktok.com/@{username}/video/{vid_id}")
    except Exception as e:
        print(f"⚠️ RapidAPI Crawl Error: {e}")
    return video_links

def get_channel_videos(channel_url, limit=5):
    """Hàm tổng hợp lấy link video"""
    print(f"🔍 Đang quét kênh: {channel_url}")

    # Thử yt-dlp trước
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'playlistend': limit,
        'ignoreerrors': True, # Bỏ qua lỗi video riêng lẻ
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    video_links = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)
            if info and 'entries' in info:
                for e in info['entries']:
                    if e:
                        v_url = e.get('url') or e.get('webpage_url')
                        if v_url: video_links.append(v_url)
    except Exception as e:
        print(f"⚠️ yt-dlp Error: {e}")

    # Nếu yt-dlp không lấy được gì, thử RapidAPI
    if not video_links:
        print("   ↳ yt-dlp thất bại, chuyển sang RapidAPI...")
        video_links = get_videos_via_rapidapi(channel_url, limit)

    return [v for v in video_links if v]

# --- PHẦN 2: DOWNLOADER (TẢI FILE) ---

def download_via_tikwm(url, save_path):
    try:
        api_url = "https://www.tikwm.com/api/"
        res = requests.post(api_url, data={'url': url, 'hd': 1}, timeout=15).json()
        if res.get('code') == 0:
            play_url = res['data']['play']
            # [FIX] Kiểm tra xem link trả về là tương đối hay tuyệt đối
            if not play_url.startswith("http"):
                v_url = "https://www.tikwm.com" + play_url
            else:
                v_url = play_url

            with requests.get(v_url, stream=True) as r:
                with open(save_path, 'wb') as f:
                    shutil.copyfileobj(r.raw, f)
            return True
    except: return False

def download_via_rapidapi(tiktok_url, save_path):
    config = load_rapid_config()
    keys = config.get("keys", [])
    host = config.get("host", "")
    api_url = config.get("endpoint", "") # Đảm bảo endpoint này là endpoint download (vd: /vid/index)

    for key in keys:
        if not key: continue
        try:
            # Lưu ý: Param 'url' hay 'link' tùy thuộc vào API document
            resp = requests.get(api_url, headers={"x-rapidapi-key": key, "x-rapidapi-host": host}, params={"url": tiktok_url}, timeout=20)

            if resp.status_code == 429: continue # Hết quota, thử key khác
            if resp.status_code != 200: continue

            result = resp.json()
            download_url = None

            # Parsing logic (Cần điều chỉnh tùy theo API Rapid cụ thể bạn mua)
            if isinstance(result, dict):
                # Ưu tiên link HD hoặc link no-watermark
                download_url = result.get("video_hd") or result.get("video") or result.get("play")
                if isinstance(download_url, list): download_url = download_url[0]

            if download_url:
                with requests.get(download_url, stream=True) as r:
                    with open(save_path, 'wb') as f: shutil.copyfileobj(r.raw, f)
                return True
        except: continue
    return False

def download_tiktok_video(url, temp_dir):
    """Hàm tải video chính với quy trình 3 bước + FIX WinError 32"""
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    try:
        video_id = url.split("video/")[1].split("?")[0]
    except:
        video_id = str(int(time.time()))

    # [FIX QUAN TRỌNG] Thêm Timestamp vào tên file
    # Để tránh lỗi "File used by another process" nếu file cũ chưa kịp xóa
    timestamp = int(time.time())
    final_path = os.path.join(temp_dir, f"src_{video_id}_{timestamp}.mp4")

    print(f"   ⬇️ Downloading: {url}")

    # 1. Thử TikWM
    if download_via_tikwm(url, final_path):
        return final_path

    # 2. Thử RapidAPI (Nếu có config)
    if download_via_rapidapi(url, final_path):
        return final_path

    # 3. Fallback yt-dlp
    try:
        ydl_opts = {
            'outtmpl': final_path,
            'format': 'best',
            'quiet': True,
            'overwrites': True # Đảm bảo ghi đè
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        if os.path.exists(final_path):
            return final_path
    except Exception as e:
        print(f"   ❌ Lỗi yt-dlp: {e}")

    return None