import streamlit as st
import sys
import os

# Thêm đường dẫn root để import các module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import các trang từ module con
from ui.pages.dashboard import render_dashboard
from ui.pages.account_manager import render_account_manager
from ui.pages.channel_manager import render_channel_manager
from ui.pages.chrome_profile_manager import render_chrome_profile_manager
from ui.pages.api_settings import render_api_settings

def render_main_ui():
    st.set_page_config(page_title="Auto Clone Bot", layout="wide", page_icon="🤖")

    with st.sidebar:
        st.title("🤖 MENU QUẢN LÝ")
        menu_options = [
            "Dashboard",
            "Quản lý Tài khoản",
            "Quản lý Kênh Clone",
            "Quản lý Chrome Profile",
            "Cấu hình API"
        ]
        selection = st.radio("Chọn chức năng:", menu_options)

    if selection == "Dashboard": render_dashboard()
    elif selection == "Quản lý Tài khoản": render_account_manager()
    elif selection == "Quản lý Kênh Clone": render_channel_manager()
    elif selection == "Quản lý Chrome Profile": render_chrome_profile_manager()
    elif selection == "Cấu hình API": render_api_settings()

if __name__ == "__main__":
    render_main_ui()