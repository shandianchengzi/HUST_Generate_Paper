import streamlit as st
from streamlit_js_eval import streamlit_js_eval
import json
import hashlib
import os
import gzip
import pickle
import time
from typing import List, Dict

DEBUG = False

# 基础函数和工具类
class AppFramework:
    @staticmethod
    def generate_cache_key(prefix: str, data: str) -> str:
        """生成带前缀的缓存键名"""
        return f"{prefix}_{hashlib.md5(data.encode()).hexdigest()}"
    
    @staticmethod
    def save_to_local_cache(data: Dict):
        """保存数据到本地缓存"""
        streamlit_js_eval(
            js_expressions=f"localStorage.setItem('hust_gen_paper_cache', JSON.stringify({json.dumps(data)}))",
            key=f"save_cache_{hash(json.dumps(data))}"
        )
    
    @staticmethod
    def load_from_local_cache() -> Dict:
        """从本地缓存加载数据"""
        cached_data = streamlit_js_eval(
            js_expressions="JSON.parse(localStorage.getItem('hust_gen_paper_cache') || 'null')",
            key="load_cache"
        )
        return cached_data or {}
    
    @staticmethod
    def load_history(cache_dir: str) -> List:
        """加载历史记录"""
        if os.path.exists(cache_dir):
            cache_files = [f for f in os.listdir(cache_dir)]
            cache_files.sort(key=lambda x: os.path.getmtime(os.path.join(cache_dir, x)), reverse=True)
            return cache_files
        return []
    
    @staticmethod
    def setup_page_config():
        """设置页面配置"""
        st.set_page_config(
            page_title="多功能应用框架",
            page_icon="🚀",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        st.markdown("""
        <style>
        /* 修复所有输入框光标不可见问题 */
        [data-baseweb="textarea"] textarea,
        [data-baseweb="input"] input,
        [data-baseweb="base-input"] {
            caret-color: #4a8af4 !important;  /* 蓝色光标 */
        }
        .stTextArea [data-baseweb=base-input] {
            background-color: #f8f9fa;
            color: #000000 !important;  /* 黑色文字 */
        }
        /* 特别针对TextArea的placeholder */
        .stTextArea textarea::placeholder {
            color: #666666 !important;
        }
        .stButton>button {
            background-color: #4a8af4;
            color: white;
            font-weight: bold;
            border-radius: 8px;
            padding: 0.5rem 1rem;
        }
        .stButton>button:hover {
            background-color: #3a7ae4;
            color: white;
        }
        .header-text {
            font-size: 1.8rem;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 1rem;
        }
        .sidebar .sidebar-content {
            background-color: #f8f9fa;
        }
        /* 确保所有输入框文字可见 */
        [data-baseweb="base-input"] {
            color: #000000 !important;
        }
        textarea {
            color: #000000 !important;
        }
        textarea:focus, input:focus {
            outline: 2px solid #4a8af4 !important;  /* 聚焦时的外边框 */
            outline-offset: -1px !important;
        }
        </style>
        """, unsafe_allow_html=True)

# 多页面管理器
class PageManager:
    def __init__(self):
        self.pages = {
            "文章生成器": "paper_generator",
            # 可以在此添加更多页面
        }
        
    def show_navigation(self):
        """显示页面导航标签"""
        st.sidebar.title("导航")
        return st.sidebar.radio("选择页面", list(self.pages.keys()))
    
    def run_current_page(self, page_name: str):
        """运行当前页面"""
        if page_name == "文章生成器":
            from paper_generator import PaperGeneratorPage
            PaperGeneratorPage().render()
        # 可以在此添加更多页面的调用

# 主入口
def main():
    AppFramework.setup_page_config()
    manager = PageManager()
    current_page = manager.show_navigation()
    manager.run_current_page(current_page)

if __name__ == "__main__":
    main()