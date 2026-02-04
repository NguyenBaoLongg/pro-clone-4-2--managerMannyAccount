import undetected_chromedriver as uc
import os
import time

# ================= CẤU HÌNH ĐƯỜNG DẪN PROFILE =================
CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT_DIR = os.path.dirname(CURRENT_FILE_DIR)

# Tên thư mục chứa dữ liệu profile (Giống hệt bên file upload)
PROFILE_FOLDER_NAME = "assets/selenium_user_data"
USER_DATA_DIR = os.path.join(PROJECT_ROOT_DIR, PROFILE_FOLDER_NAME)

# Tạo thư mục nếu chưa có
if not os.path.exists(USER_DATA_DIR):
    os.makedirs(USER_DATA_DIR)

print(f"📂 Dữ liệu sẽ được lưu tại: {USER_DATA_DIR}")
# =============================================================

def manual_login():
    print("🚀 Đang khởi động Chrome để đăng nhập...")

    options = uc.ChromeOptions()
    # Dòng quan trọng nhất: Chỉ định thư mục lưu profile
    options.add_argument(f"--user-data-dir={USER_DATA_DIR}")

    # Tắt các pop-up khôi phục lỗi, lưu password
    options.add_argument("--no-first-run")
    options.add_argument("--no-service-autorun")
    options.add_argument("--password-store=basic")
    options.add_argument("--start-maximized")

    # Khởi tạo Driver
    try:
        driver = uc.Chrome(options=options, version_main=144, headless=False)
    except Exception as e:
        print(f"❌ Lỗi khởi tạo: {e}")
        print("💡 GỢI Ý: Hãy tắt tất cả cửa sổ Chrome đang mở và thử lại.")
        return

    # Mở trang đăng nhập TikTok
    print("🔗 Đang truy cập TikTok...")
    driver.get("https://www.tiktok.com/login")

    print("\n" + "="*50)
    print("⚠️ HƯỚNG DẪN:")
    print("1. Trình duyệt đã mở. Hãy đăng nhập thủ công (Quét QR, Email, Google...).")
    print("2. Sau khi đăng nhập thành công và thấy trang chủ TikTok.")
    print("3. QUAY LẠI CỬA SỔ ĐEN NÀY VÀ NHẤN PHÍM 'ENTER' ĐỂ LƯU VÀ THOÁT.")
    print("="*50 + "\n")

    # Treo tool ở đây chờ người dùng nhấn Enter
    input("👉 ĐÃ ĐĂNG NHẬP XONG? Nhấn [ENTER] để đóng tool và lưu cookie...")

    print("💾 Đang lưu dữ liệu và thoát...")
    driver.quit()
    print("✅ Đã xong! Bạn có thể chạy tool Upload ngay bây giờ.")

if __name__ == "__main__":
    manual_login()