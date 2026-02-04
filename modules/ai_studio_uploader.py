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

# Định nghĩa folder Assets
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
if not os.path.exists(ASSETS_DIR): os.makedirs(ASSETS_DIR)

# Các folder con
USER_DATA_DIR = os.path.join(ASSETS_DIR, "selenium_user_data")
TEMP_DIR = os.path.join(ASSETS_DIR, "temp_downloads")

if not os.path.exists(TEMP_DIR): os.makedirs(TEMP_DIR)
# ======================================================

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

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR,
                headless=False,
                channel="chrome",
                args=["--start-maximized", "--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-infobars"],
                viewport=None
            )
        except Exception as e:
            print(f"❌ Lỗi khởi động Chrome: {e}. Hãy xóa folder 'ai_studio_data'.")
            return False

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
            time.sleep(3)

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
                time.sleep(5)
            else:
                print("❌ Lỗi: Không thấy ô Upload.")
                return False

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
                return False

            print("⏳ Chờ AI xử lý (Giữ tương tác)...")
            save_selectors = ['button:has-text("Lưu vào Sheet")', 'button:has-text("Save to Sheet")', 'button.bg-blue-600:has-text("Lưu")']
            resume_selectors = ['button:has-text("Launch")', 'button:has-text("Resume")', 'button:has-text("Continue")']

            clicked_save = False
            for i in range(60): # Max 5 phút
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
                print("🎉 XONG!"); time.sleep(5); return True
            else:
                print("❌ Timeout."); return False

        except Exception as e:
            print(f"❌ Lỗi Runtime: {e}"); return False
        finally:
            try: browser.close()
            except: pass



if __name__ == "__main__":
    run_ai_studio_uploader(r"D:\workspace\Python\App\only-clone\assets\temp_downloads\src_7602865180183252231_1770193277.mp4")