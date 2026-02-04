import json
import time
import os
import sys
import random
import glob
import subprocess

# Thư viện Selenium & Undetected Chromedriver
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# ================= CẤU HÌNH ĐƯỜNG DẪN =================
CURRENT_SCRIPT_PATH = os.path.abspath(__file__)
MODULES_DIR = os.path.dirname(CURRENT_SCRIPT_PATH)
PROJECT_ROOT = os.path.dirname(MODULES_DIR)

SETTINGS_PATH = os.path.join(PROJECT_ROOT, "user_settings.json")
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
if not os.path.exists(ASSETS_DIR): os.makedirs(ASSETS_DIR)

# Folder lưu Profile Chrome (Giữ nguyên, không xóa)
USER_DATA_DIR = os.path.join(ASSETS_DIR, "selenium_user_data")
TEMP_DIR = os.path.join(ASSETS_DIR, "temp_downloads")

if not os.path.exists(TEMP_DIR): os.makedirs(TEMP_DIR)
if not os.path.exists(USER_DATA_DIR): os.makedirs(USER_DATA_DIR)
# ======================================================

def load_settings():
    if not os.path.exists(SETTINGS_PATH):
        return None, None, None, None
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return (data.get("ai_studio_url"), data.get("video_path"), data.get("google_email"), data.get("google_password"))
    except: return None, None, None, None

def get_target_video_file(settings_video_path):
    if settings_video_path and os.path.exists(settings_video_path):
        return settings_video_path
    list_files = glob.glob(os.path.join(TEMP_DIR, "*.mp4"))
    if list_files:
        return max(list_files, key=os.path.getctime)
    return None

def click_element_safe(driver, element):
    try: element.click()
    except: driver.execute_script("arguments[0].click();", element)

def handle_google_login(driver, email, password):
    print("🕵️ Kiểm tra đăng nhập Google...")
    try:
        # Check nhanh nếu đã vào được trang đích thì thôi
        if "ai.studio" in driver.current_url:
            print("✅ Đã có phiên đăng nhập (Cookies cũ).")
            return True

        if "accounts.google.com" not in driver.current_url:
            try: driver.find_element(By.CSS_SELECTOR, 'input[type="email"]')
            except:
                print("✅ Có vẻ đã đăng nhập.")
                return True

        print("⚠️ Chưa đăng nhập, tiến hành login...")
        if not email or not password:
            print("⚠️ Thiếu Email/Pass trong cài đặt.")
            return False

        try:
            email_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="email"]')))
            email_input.clear()
            email_input.send_keys(email)
            time.sleep(1)
            email_input.send_keys(Keys.ENTER)
            time.sleep(3)
        except: pass

        try:
            pass_input = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'input[type="password"]')))
            pass_input.click()
            pass_input.send_keys(password)
            time.sleep(1)
            pass_input.send_keys(Keys.ENTER)
            time.sleep(5)
        except: pass

        return True
    except: return False

# ======================================================
# HÀM CHÍNH
# ======================================================
def run_ai_studio_uploader(input_video_path=None):
    target_url, settings_video, gg_email, gg_pass = load_settings()

    if input_video_path and os.path.exists(input_video_path):
        final_video_path = input_video_path
        print(f"🎯 Upload video: {final_video_path}")
    else:
        final_video_path = get_target_video_file(settings_video)

    if not final_video_path:
        print(f"❌ KHÔNG TÌM THẤY VIDEO!")
        return False

    MAX_RETRIES = 2
    for attempt in range(MAX_RETRIES):
        print(f"\n🚀 BẮT ĐẦU (Lần {attempt + 1})")
        print(f"📂 Sử dụng Profile cũ tại: {USER_DATA_DIR}")

        driver = None
        try:
            # --- TẠO OPTIONS MỚI MỖI LẦN CHẠY (Fix lỗi reuse) ---
            options = uc.ChromeOptions()
            # Dòng này quan trọng: Trỏ về đúng folder cũ để lấy cookies
            options.add_argument(f"--user-data-dir={USER_DATA_DIR}")

            options.add_argument("--no-sandbox")
            options.add_argument("--disable-infobars")
            options.add_argument("--disable-features=Translate")

            # Khởi tạo driver
            driver = uc.Chrome(options=options, version_main=144, user_data_dir=USER_DATA_DIR, use_subprocess=True)
            driver.maximize_window()

            # Vào trang web
            driver.get(target_url)
            time.sleep(5)

            # Xử lý đăng nhập (Nếu cookies cũ còn sống, hàm này sẽ lướt qua nhanh)
            try:
                btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Log in') or contains(text(), 'Sign in')]")
                click_element_safe(driver, btn)
            except: pass

            handle_google_login(driver, gg_email, gg_pass)

            try:
                btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Continue to the app')]")
                click_element_safe(driver, btn)
            except: pass

            # Chọn chế độ Viral Clone
            print("🔄 Chọn chế độ 'Video Viral Clone'...")
            switched = False

            def find_and_click_mode():
                xpaths = ["//*[contains(text(), 'Video Viral Clone')]", "//div[contains(., 'Viral')]"]
                for xp in xpaths:
                    try:
                        els = driver.find_elements(By.XPATH, xp)
                        for el in els:
                            if el.is_displayed():
                                click_element_safe(driver, el)
                                return True
                    except: pass
                return False

            if find_and_click_mode(): switched = True
            else:
                iframes = driver.find_elements(By.TAG_NAME, "iframe")
                for iframe in iframes:
                    try:
                        driver.switch_to.frame(iframe)
                        if find_and_click_mode():
                            switched = True
                            driver.switch_to.default_content()
                            break
                        driver.switch_to.default_content()
                    except: driver.switch_to.default_content()

            if not switched:
                print("❌ Không thấy nút Mode. (Vui lòng kiểm tra Login)")
                # Nếu lần đầu lỗi, có thể do chưa login -> Retry
                raise Exception("Mode fail")

            time.sleep(5)

            # Upload Video (Deep Injection)
            print("📤 Đang gửi file video...")
            upload_done = False

            def inject_file(drv):
                try:
                    inp = drv.find_element(By.CSS_SELECTOR, 'input[type="file"]')
                    drv.execute_script("arguments[0].style.display = 'block'; arguments[0].style.visibility = 'visible';", inp)
                    inp.send_keys(final_video_path)
                    drv.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", inp)
                    return True
                except: return False

            if inject_file(driver):
                upload_done = True
            else:
                iframes = driver.find_elements(By.TAG_NAME, "iframe")
                for iframe in iframes:
                    try:
                        driver.switch_to.frame(iframe)
                        if inject_file(driver):
                            upload_done = True
                            driver.switch_to.default_content()
                            break
                        driver.switch_to.default_content()
                    except: driver.switch_to.default_content()

            if not upload_done:
                print("❌ Không thể upload file.")
                raise Exception("Upload Failed")

            print("✅ Đã gửi lệnh upload. Chờ web phản hồi...")
            time.sleep(15)

            # Click Start
            print("▶️ Click Bắt đầu...")
            start_xpaths = ["//button[contains(text(), 'Bắt đầu')]", "//button[contains(text(), 'Start')]"]
            clicked = False

            def click_start():
                for xp in start_xpaths:
                    try:
                        btn = driver.find_element(By.XPATH, xp)
                        if btn.is_displayed():
                            click_element_safe(driver, btn)
                            return True
                    except: pass
                return False

            if click_start(): clicked = True
            else:
                iframes = driver.find_elements(By.TAG_NAME, "iframe")
                for iframe in iframes:
                    try:
                        driver.switch_to.frame(iframe)
                        if click_start():
                            clicked = True
                            driver.switch_to.default_content()
                            break
                        driver.switch_to.default_content()
                    except: driver.switch_to.default_content()

            if not clicked: print("⚠️ Không thấy nút Start.")

            # Chờ kết quả
            print("⏳ Chờ kết quả AI...")
            save_xpaths = ["//button[contains(text(), 'Lưu vào Sheet')]", "//button[contains(text(), 'Save to Sheet')]"]
            success = False

            for i in range(60):
                for xp in save_xpaths:
                    try:
                        el = driver.find_element(By.XPATH, xp)
                        if el.is_displayed():
                            click_element_safe(driver, el)
                            success = True; break
                    except: pass
                if success: break

                iframes = driver.find_elements(By.TAG_NAME, "iframe")
                for iframe in iframes:
                    try:
                        driver.switch_to.frame(iframe)
                        for xp in save_xpaths:
                            try:
                                el = driver.find_element(By.XPATH, xp)
                                if el.is_displayed():
                                    click_element_safe(driver, el)
                                    success = True; break
                            except: pass
                        driver.switch_to.default_content()
                        if success: break
                    except: driver.switch_to.default_content()
                if success: break

                if i % 2 == 0: print(f"... chờ {i*5}s")
                time.sleep(5)

            if success:
                print("🎉 THÀNH CÔNG! Đã lưu.")
                time.sleep(3)
                driver.quit()
                return True
            else:
                print("❌ Hết giờ chờ.")
                raise Exception("Timeout")

        except Exception as e:
            print(f"❌ Lỗi: {e}")
            if driver: driver.quit()
            if attempt < MAX_RETRIES - 1: continue
            return False

    return False

if __name__ == "__main__":
    run_ai_studio_uploader()