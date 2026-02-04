import streamlit as st
from ui.sidebar import render_sidebar
from ui.auto_bot_ui import render_auto_bot_page

# 1. Setup trang (Phải nằm đầu tiên)
st.set_page_config(page_title="EverAI System", layout="wide")

# 2. Render Sidebar và lấy kết quả chọn
selected_page_name = render_sidebar()

# 3. Render Màn hình chính dựa trên kết quả chọn
render_auto_bot_page(selected_page_name)