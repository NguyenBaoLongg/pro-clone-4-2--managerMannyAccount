import json
from playwright.sync_api import sync_playwright
import time
import os
import sys
import random
import glob
import subprocess

# ================= CẤU HÌNH ĐƯỜNG DẪN =================
CURRENT_SCRIPT_PATH = os.path.abspath(__file__)
MODULES_DIR = os.path.dirname(CURRENT_SCRIPT_PATH)
PROJECT_ROOT = os.path.dirname(MODULES_DIR)

SETTINGS_PATH = os.path.join(PROJECT_ROOT, "user_settings.json")
# [THÊM] Đường dẫn file config session để lưu vị trí profile hiện tại
SESSION_CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "session_config.json")

# Định nghĩa folder Assets
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
if not os.path.exists(ASSETS_DIR): os.makedirs(ASSETS_DIR)
AI_STUDIO_DIR = os.path.join(ASSETS_DIR, "ai_studio_data")
# Các folder con
# [LƯU Ý] Biến cũ này vẫn giữ nguyên để không vi phạm quy tắc xóa, nhưng sẽ được override trong hàm main
USER_DATA_DIR = os.path.join(AI_STUDIO_DIR, "YarleyVespery@vizatv.dpdns.org")
TEMP_DIR = os.path.join(ASSETS_DIR, "temp_downloads")

if not os.path.exists(TEMP_DIR): os.makedirs(TEMP_DIR)
# [THÊM] Tạo folder config nếu chưa có
if not os.path.exists(os.path.dirname(SESSION_CONFIG_PATH)): os.makedirs(os.path.dirname(SESSION_CONFIG_PATH))

# ======================================================

# [THÊM] Hàm lấy danh sách các folder profile chrome
def get_chrome_profiles():
    if not os.path.exists(AI_STUDIO_DIR):
        return []
    # Lấy tất cả các folder con trong ai_studio_data
    profiles = [d for d in os.listdir(AI_STUDIO_DIR) if os.path.isdir(os.path.join(AI_STUDIO_DIR, d))]
    profiles.sort() # Sắp xếp để thứ tự index cố định
    return profiles

# [THÊM] Hàm đọc index hiện tại từ config
def get_current_profile_index():
    if not os.path.exists(SESSION_CONFIG_PATH):
        return 0
    try:
        with open(SESSION_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return int(data.get("ai_studio_current", 0))
    except: return 0

# [THÊM] Hàm cập nhật index mới vào config
def update_profile_index(new_index):
    data = {}
    if os.path.exists(SESSION_CONFIG_PATH):
        try:
            with open(SESSION_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except: pass

    data["ai_studio_current"] = new_index
    try:
        with open(SESSION_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        print(f"📝 [Multi-Profile] Đã lưu index profile mới: {new_index}")
    except Exception as e:
        print(f"⚠️ Không thể lưu session config: {e}")

def load_settings():
    if not os.path.exists(SETTINGS_PATH):
        print(f"❌ [Module AI] Không tìm thấy file settings tại: {SETTINGS_PATH}")
        return None, None, None, None
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            # video_path ở đây có thể là URL hoặc đường dẫn local
            return (data.get("ai_studio_url"), data.get("video_path"), data.get("google_email"), data.get("google_password"))
    except Exception as e:
        print(f"❌ [Module AI] Lỗi đọc JSON: {e}")
        return None, None, None, None

def kill_chrome_processes():
    try:
        if sys.platform == "win32":
            subprocess.run("taskkill /f /im chrome.exe", shell=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            time.sleep(1)
    except: pass

# [MỚI] Hàm tự tìm file video cần upload
def get_target_video_file(settings_video_path):
    # Ưu tiên 1: Nếu settings có đường dẫn file local hợp lệ
    if settings_video_path and os.path.exists(settings_video_path):
        return settings_video_path

    # Ưu tiên 2: Quét file mới nhất trong folder temp_downloads
    print(f"🔍 Đang tìm video trong: {TEMP_DIR}")
    list_files = glob.glob(os.path.join(TEMP_DIR, "*.mp4"))
    if list_files:
        latest_file = max(list_files, key=os.path.getctime)
        return latest_file

    return None

def handle_google_login(page, email, password):
    print("🕵️ Kiểm tra đăng nhập Google...")
    try:
        if "accounts.google.com" in page.url or page.locator('input[type="email"]').count() > 0:
            if not email or not password:
                print("⚠️ Thiếu Email/Pass. Chờ 60s để nhập tay...")
                time.sleep(60); return

            email_input = page.locator('input[type="email"]')
            if email_input.is_visible():
                email_input.fill(email); time.sleep(1)
                page.keyboard.press("Enter"); time.sleep(5)

            pass_input = page.locator('input[type="password"]')
            try: pass_input.wait_for(state="visible", timeout=10000)
            except: pass

            if pass_input.is_visible():
                pass_input.click(); pass_input.fill(password)
                time.sleep(1); page.keyboard.press("Enter")

            print("✅ Đã Login."); page.wait_for_url("**/ai.studio/**", timeout=60000)
        else:
            print("✅ Đã đăng nhập sẵn.")
    except Exception as e:
        print(f"⚠️ Lỗi login (Bỏ qua): {e}")

def run_ai_studio_uploader(local_video_path):
    print("🧹 Dọn dẹp Chrome cũ...")
    # kill_chrome_processes()

    target_url, settings_video, gg_email, gg_pass = load_settings()

    if not target_url:
        print("❌ Thiếu AI Studio URL.")
        return False

    # [FIX] Lấy file video động (không hardcode)
    final_video_path = local_video_path

    if not final_video_path:
        print(f"❌ LỖI: Không tìm thấy file video nào để upload!")
        print(f"👉 Vui lòng kiểm tra folder: {TEMP_DIR}")
        return False

    print(f"🚀 [Module AI] Bắt đầu upload file: {os.path.basename(final_video_path)}")

    if sys.platform == 'win32':
        import asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    # [THÊM] LOGIC QUẢN LÝ ĐA PROFILE -----------------------------------------
    profiles = get_chrome_profiles()
    if not profiles:
        print("❌ Không tìm thấy profile nào trong assets/ai_studio_data")
        return False

    # Số lần thử tối đa bằng số lượng profile (để tránh lặp vô hạn nếu tất cả đều lỗi)
    max_profile_retries = len(profiles)

    for attempt_idx in range(max_profile_retries):
        # Lấy index hiện tại từ config
        current_profile_idx = get_current_profile_index()

        # Đảm bảo index hợp lệ
        if current_profile_idx >= len(profiles):
            current_profile_idx = 0
            update_profile_index(0)

        profile_name = profiles[current_profile_idx]
        # [QUAN TRỌNG] Override biến USER_DATA_DIR cục bộ theo profile hiện tại
        current_user_data_dir = os.path.join(AI_STUDIO_DIR, profile_name)

        print(f"\n==================================================")
        print(f"👤 [Multi-Profile] Đang chạy Profile ({current_profile_idx + 1}/{len(profiles)}): {profile_name}")
        print(f"📂 Path: {current_user_data_dir}")
        print(f"==================================================")

        # Cờ đánh dấu thành công cho lần chạy này
        this_run_success = False

        try:
            with sync_playwright() as p:
                try:
                    browser = p.chromium.launch_persistent_context(
                        user_data_dir=current_user_data_dir, # Sử dụng đường dẫn profile động
                        headless=False,
                        channel="chrome",
                        args=["--start-maximized", "--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-infobars"],
                        viewport=None
                    )
                except Exception as e:
                    print(f"❌ Lỗi khởi động Chrome (Profile: {profile_name}): {e}")
                    # Chuyển tiếp profile ngay tại đây
                    raise Exception("Chrome Launch Failed")

                try:
                    page = browser.pages[0]
                    print("🔗 Truy cập AI Studio...")
                    page.goto(target_url, timeout=60000)
                    time.sleep(3)

                    try:
                        login_btn = page.locator('button:has-text("Log in"), button:has-text("Sign in")').first
                        if login_btn.is_visible(timeout=3000): login_btn.click()
                    except: pass

                    handle_google_login(page, gg_email, gg_pass)

                    try: page.wait_for_load_state("networkidle", timeout=10000)
                    except: pass

                    try:
                        continue_btn = page.locator('button:has-text("Continue to the app")')
                        if continue_btn.is_visible(timeout=5000): continue_btn.click(); time.sleep(2)
                    except: pass

                    print("🔍 Tìm App 'Video Viral Clone'...")
                    app_btn_selector = 'button:has-text("Video Viral Clone")'
                    clicked_app = False
                    all_frames = [page.main_frame] + page.frames
                    for frame in all_frames:
                        try:
                            btn = frame.locator(app_btn_selector).first
                            if btn.is_visible():
                                btn.scroll_into_view_if_needed(); btn.click(force=True)
                                clicked_app = True; break
                        except: continue

                    if not clicked_app:
                        try:
                            css_btn = page.locator('button.text-slate-500').filter(has_text="Video Viral Clone").first
                            if css_btn.is_visible(timeout=3000): css_btn.click(force=True); clicked_app = True
                        except: pass

                    if not clicked_app: print("⚠️ Có thể đã vào App sẵn...")
                    time.sleep(15)

                    print("📤 Upload Video...")
                    upload_selector = 'input[type="file"][accept="video/*"]'
                    file_input = None

                    all_frames = [page.main_frame] + page.frames
                    for frame in all_frames:
                        try:
                            locator = frame.locator(upload_selector).first
                            if locator.count() > 0: file_input = locator; break
                        except: continue

                    if file_input:
                        file_input.wait_for(state="attached", timeout=15000)
                        file_input.set_input_files(final_video_path)
                        print("✅ Upload thành công!")
                        time.sleep(10)
                    else:
                        print("❌ Lỗi: Không thấy ô Upload.")
                        # [THÊM] Nếu không thấy ô upload, coi như lỗi -> Chuyển profile
                        raise Exception("Upload Input Not Found")

                    print("▶️ Click 'Bắt đầu Clone Viral'...")
                    start_btn_selector = 'button:has-text("Bắt đầu Clone Viral")'
                    clicked_start = False
                    all_frames = [page.main_frame] + page.frames
                    for frame in all_frames:
                        try:
                            start_btn = frame.locator(start_btn_selector).first
                            if start_btn.is_visible(timeout=5000):
                                start_btn.scroll_into_view_if_needed(); start_btn.click(force=True)
                                clicked_start = True; break
                        except: continue

                    if not clicked_start:
                        print("❌ Không thấy nút Start.")
                        raise Exception("Start Button Not Found")

                    print("⏳ Chờ AI xử lý (Giữ tương tác)...")
                    save_selectors = ['button:has-text("Lưu vào Sheet")', 'button:has-text("Save to Sheet")', 'button.bg-blue-600:has-text("Lưu")']
                    resume_selectors = ['button:has-text("Launch")', 'button:has-text("Resume")', 'button:has-text("Continue")']

                    clicked_save = False
                    for i in range(40): # Max 5 phút
                        all_frames = [page.main_frame] + page.frames

                        # Check nút Lưu
                        for frame in all_frames:
                            for selector in save_selectors:
                                try:
                                    save_btn = frame.locator(selector).first
                                    if save_btn.is_visible():
                                        print(f"✅ Thấy nút Lưu! Click...");
                                        save_btn.scroll_into_view_if_needed(); save_btn.click(force=True)
                                        clicked_save = True; break
                                except: continue
                            if clicked_save: break
                        if clicked_save: break

                        # Giữ tương tác
                        try:
                            vp = page.viewport_size or {'width':1280, 'height':720}
                            page.mouse.move(random.randint(10, vp['width']-10), random.randint(10, vp['height']-10))
                            if i % 5 == 0: page.mouse.click(10, 10) # Click góc để chống ngủ

                            for frame in all_frames:
                                for res_sel in resume_selectors:
                                    try:
                                        res_btn = frame.locator(res_sel).first
                                        if res_btn.is_visible(timeout=500):
                                            print("🚀 Click Resume..."); res_btn.click(force=True); time.sleep(1)
                                    except: continue
                        except: pass

                        if i % 2 == 0: print(f"... Chờ ({i+1}/60)")
                        time.sleep(5)

                    if clicked_save:
                        print("🎉 XONG! Profile này hoạt động tốt."); time.sleep(5)
                        this_run_success = True
                        return True # [QUAN TRỌNG] Trả về True ngay nếu thành công
                    else:
                        print("❌ Timeout nút Lưu (Có thể lỗi xử lý).")
                        raise Exception("Timeout waiting for Save button")

                except Exception as e:
                    print(f"❌ Lỗi Runtime trong profile {profile_name}: {e}")
                    raise e # Ném lỗi ra ngoài để vòng lặp bắt được và chuyển profile
                finally:
                    try: browser.close()
                    except: pass

        except Exception as e:
            print(f"⚠️ [Multi-Profile] Phát hiện lỗi ở Profile hiện tại: {e}")
            print("🔄 Đang chuyển sang Profile tiếp theo...")

            # Tính toán index tiếp theo
            next_index = (current_profile_idx + 1) % len(profiles)
            update_profile_index(next_index)

            # Đợi một chút trước khi thử lại
            time.sleep(3)
            continue # Chuyển sang vòng lặp tiếp theo (Profile mới)

    # Kết thúc vòng lặp mà không return True -> Tất cả đều lỗi
    print("❌ [Multi-Profile] Đã thử tất cả Profile nhưng đều thất bại!")
    return False

if __name__ == "__main__":
    run_ai_studio_uploader(r"D:\workspace\Python\App\only-clone\assets\temp_downloads\src_7602865180183252231_1770193277.mp4")