import streamlit as st
from streamlit_js_eval import streamlit_js_eval
import json
from typing import List, Dict
import hashlib
# for history
import os
import gzip
import pickle
import time
file_dir = os.path.dirname(__file__)

DEBUG = False

from agent import agent

# 模拟的大模型接口调用函数
def generate_result(prompt: str) -> str:
    """
    本地的大模型接口调用
    """
    return agent.simple_request(prompt)

def generate_prompt(prompt: str, requirements: List[str]) -> str:
    """
    生成prompt
    """
    return f"原始文本：\n{prompt}\n\n修改要求如下:\n" + "\n".join(requirements)


# 生成缓存键名
def generate_cache_key(prefix: str, data: str) -> str:
    """生成带前缀的缓存键名"""
    return f"{prefix}_{hashlib.md5(data.encode()).hexdigest()}"

# 默认要求
DEFAULT_REQUIREMENTS = [
    "请帮我适当缩短文本篇幅，保证可阅读性，并将术语更加易懂化或减少，保证大一新生也能读懂，但不改变原有的结构和严谨性，并且不使用任何比喻、类比的修辞手法，保证文本的严肃性。",
    "我希望你能保留{主题}相关的内容，因为我这个内容用意是介绍{主题}。"
]

# 初始化session state
def init_session_state():
    if 'hust_gen_paper_step' not in st.session_state:
        st.session_state.hust_gen_paper_step = 1
    if 'hust_gen_paper_outlines' not in st.session_state:
        st.session_state.hust_gen_paper_outlines = []
    if 'hust_gen_paper_references' not in st.session_state:
        st.session_state.hust_gen_paper_references = []
    if 'hust_gen_paper_requirements' not in st.session_state:
        st.session_state.hust_gen_paper_requirements = DEFAULT_REQUIREMENTS.copy()
    if 'hust_gen_paper_theme' not in st.session_state:
        st.session_state.hust_gen_paper_theme = ""
    if 'hust_gen_paper_outlines_text' not in st.session_state:
        st.session_state.hust_gen_paper_outlines_text = ""
    if 'hust_gen_paper_generated_text' not in st.session_state:
        st.session_state.hust_gen_paper_generated_text = ""
    if 'hust_gen_paper_final_text' not in st.session_state:
        st.session_state.hust_gen_paper_final_text = ""

# 保存数据到本地缓存
def save_to_local_cache():
    data = {
        'theme': st.session_state.hust_gen_paper_theme,
        'outlines': st.session_state.hust_gen_paper_outlines,
        'references': st.session_state.hust_gen_paper_references,
        'requirements': st.session_state.hust_gen_paper_requirements,
        'outlines_text': st.session_state.hust_gen_paper_outlines_text,
        'req_selected': st.session_state.hust_req_selected,  # 新增：保存选择状态
        'generated_text': st.session_state.hust_gen_paper_generated_text,
        'final_text': st.session_state.hust_gen_paper_final_text
    }
    # 保存到浏览器localStorage
    streamlit_js_eval(
        js_expressions=f"localStorage.setItem('hust_gen_paper_cache', JSON.stringify({json.dumps(data)}))",
        key=f"save_cache_{hash(json.dumps(data))}"  # 唯一key确保每次保存都能触发
    )
    if DEBUG:
        print("\n=== 调试信息：保存到localStorage ===")
        print("hust_gen_paper_cache:", data)

def load_from_local_cache():
    # 防止重复加载的标记
    if '_cache_loaded' not in st.session_state:
        st.session_state._cache_loaded = False
    
    # 如果已经加载过则跳过
    if st.session_state._cache_loaded:
        # 跳过重复加载
        return

    # 从浏览器localStorage获取数据
    cached_data = streamlit_js_eval(
        js_expressions="JSON.parse(localStorage.getItem('hust_gen_paper_cache') || 'null')",
        key="load_cache"
    )
    
    if DEBUG:
        print("\n=== 调试信息：从localStorage加载 ===")
        print("hust_gen_paper_cache:", cached_data)
    
    if cached_data and isinstance(cached_data, dict):
        st.session_state.hust_gen_paper_theme = cached_data.get('theme', "")
        st.session_state.hust_gen_paper_outlines = cached_data.get('outlines', [])
        st.session_state.hust_gen_paper_references = cached_data.get('references', [])
        st.session_state.hust_gen_paper_requirements = cached_data.get('requirements', DEFAULT_REQUIREMENTS.copy())
        st.session_state.hust_gen_paper_outlines_text = cached_data.get('outlines_text', "")
        st.session_state.hust_req_selected = cached_data.get('req_selected', [True] * len(st.session_state.hust_gen_paper_requirements))  # 新增：加载选择状态
        st.session_state.hust_gen_paper_generated_text = cached_data.get('generated_text', "")
        st.session_state.hust_gen_paper_final_text = cached_data.get('final_text', "")
        # 标记已加载
        st.session_state._cache_loaded = True
    elif DEBUG:
        print("未找到有效的缓存数据")

# 更新主题的函数
def update_theme(new_theme):
    st.session_state.hust_gen_paper_theme = new_theme
    save_to_local_cache()

# 添加更新大纲的函数
def update_outlines(new_outlines):
    st.session_state.hust_gen_paper_outlines_text = new_outlines
    save_to_local_cache()

# 添加更新提示词的函数
def update_prompt(new_prompt):
    st.session_state.hust_gen_paper_generated_text = new_prompt
    save_to_local_cache()

# 添加重置函数
def reset_to_defaults():   
    # 重置session_state
    st.session_state.hust_gen_paper_theme = ""
    st.session_state.hust_gen_paper_outlines = []
    st.session_state.hust_gen_paper_references = []
    st.session_state.hust_gen_paper_requirements = DEFAULT_REQUIREMENTS.copy()
    st.session_state.hust_gen_paper_outlines_text = ""
    st.session_state.hust_gen_paper_generated_text = ""
    st.session_state.hust_gen_paper_final_text = ""
    st.session_state.hust_gen_paper_step = 1
    save_to_local_cache()

# 第一步：输入主题和大纲
def render_step1():
    st.header("1. 输入主题和大纲")
    
    # 恢复默认按钮 - 放在主题输入框上方
    if st.button("🔄 恢复默认设置", key="hust_gen_paper_reset_defaults"):
        reset_to_defaults()
    
    theme = st.text_input(
        "文章主题", 
        value=st.session_state.hust_gen_paper_theme,
        key="hust_gen_paper_theme_input",
        placeholder="请输入文章主题，例如：人工智能的发展历史",
        on_change=lambda: update_theme(st.session_state.hust_gen_paper_theme_input)
    )
    
    outlines_text = st.text_area(
        "文章大纲（每行一个要点）", 
        value=st.session_state.hust_gen_paper_outlines_text,
        key="hust_gen_paper_outlines_input",
        height=300,
        placeholder="请输入文章大纲，每行一个要点。例如：\n1. 人工智能的定义\n2. 人工智能的发展阶段\n3. 当前人工智能的应用领域",
        on_change=lambda: update_outlines(st.session_state.hust_gen_paper_outlines_input)
    )
    
    if st.button("下一步", key="hust_gen_paper_step1_next"):
        if not theme.strip():
            st.error("请输入文章主题")
            return
        if not outlines_text.strip():
            st.error("请输入文章大纲")
            return
            
        st.session_state.hust_gen_paper_theme = theme.strip()
        st.session_state.hust_gen_paper_outlines_text = outlines_text.strip()
        outlines = [line.strip() for line in outlines_text.split('\n') if line.strip()]
        st.session_state.hust_gen_paper_outlines = outlines
        
        st.session_state.hust_gen_paper_step = 2
        save_to_local_cache()
        st.rerun()

# 第二步：输入参考文本
def render_step2():
    st.header("2. 输入参考文本")
    st.write("参考文本太复杂的时候，建议找个网页大模型，用网页大模型回炉重造一下参考文本，提示词可以用'概括一下是什么研究，我要作为参考文献引入的：'。")
    st.write(f"主题: {st.session_state.hust_gen_paper_theme}")
    
    # 返回上一步按钮
    if st.button("返回上一步", key="hust_gen_paper_step2_back"):
        st.session_state.hust_gen_paper_step = 1
        save_to_local_cache()
        st.rerun()
    
    # 显示每个大纲点的参考文本输入框
    for i, outline in enumerate(st.session_state.hust_gen_paper_outlines):
        st.subheader(f"大纲要点 {i+1}")
        st.write(outline)
        
        # 确保参考文本列表长度足够
        while len(st.session_state.hust_gen_paper_references) <= i:
            st.session_state.hust_gen_paper_references.append("")
        
        reference = st.text_area(
            f"参考文本 {i+1}", 
            value=st.session_state.hust_gen_paper_references[i],
            key=f"hust_gen_paper_reference_{i}",
            height=150,
            placeholder=f"请输入关于'{outline}'的参考文本",
            on_change=lambda i=i: (
                st.session_state.hust_gen_paper_references.__setitem__(
                    i, st.session_state[f"hust_gen_paper_reference_{i}"]
                ),
                save_to_local_cache()
            )
        )
    
    # 生成文章按钮
    if st.button("生成文章", key="hust_gen_paper_generate"):
        # 准备提示
        prompt = f"{st.session_state.hust_gen_paper_theme}\n"
        for outline, reference in zip(st.session_state.hust_gen_paper_outlines, st.session_state.hust_gen_paper_references):
            prompt += f"{outline}\n"
            if reference:
                prompt += f"  {reference}\n"
        
        # 只处理用户选择的要求（带自动编号）
        selected_requirements = []
        order = 1
        for i, (req, is_selected) in enumerate(zip(st.session_state.hust_gen_paper_requirements, 
                                                 st.session_state.hust_req_selected), 1):
            if is_selected:
                # 替换主题参数并添加编号
                processed_req = req.replace("{主题}", st.session_state.hust_gen_paper_theme)
                selected_requirements.append(f"{order}. {processed_req}")
                order += 1
        
        # 调用大模型生成提示词
        with st.spinner("正在生成提示词，请稍候..."):
            generated_text = generate_prompt(prompt, selected_requirements)
        
        st.session_state.hust_gen_paper_generated_text = generated_text
        st.session_state.hust_gen_paper_step = 3
        save_to_local_cache()
        st.rerun()

# 第三步：显示提示词并生成文章
def render_step3():
    st.header("3. 提示词生成")
    st.write(f"主题: {st.session_state.hust_gen_paper_theme}")
    
    # 返回按钮
    col1, col2 = st.columns(2)
    with col1:
        if st.button("返回修改参考文本", key="hust_gen_paper_step3_back"):
            st.session_state.hust_gen_paper_step = 2
            st.rerun()
    with col2:
        if st.button("重新开始", key="hust_gen_paper_step3_restart"):
            reset_to_defaults()
            st.rerun()
    
    # 显示生成的提示词
    st.subheader("生成的提示词内容")
    st.text_area(
        "提示词内容", 
        value=st.session_state.hust_gen_paper_generated_text,
        height=500,
        key="hust_gen_paper_generated_text_display",
        label_visibility="collapsed",
        on_change=lambda: update_prompt(st.session_state.hust_gen_paper_generated_text_display)
    )
    
    # 生成最终文章按钮
    if st.button("生成最终文章", key="hust_gen_paper_generate_final"):
        with st.spinner("正在生成文章，请稍候..."):
            final_text = generate_result(st.session_state.hust_gen_paper_generated_text_display)
        
        st.session_state.hust_gen_paper_final_text = final_text
        st.session_state.hust_gen_paper_step = 4
        save_to_local_cache()
        st.rerun()

# 第四步：显示最终生成的文章
def render_step4():
    st.header("4. 文章生成结果")
    st.write(f"主题: {st.session_state.hust_gen_paper_theme}")
    
    # 返回按钮
    col1, col2 = st.columns(2)
    with col1:
        if st.button("返回修改提示词", key="hust_gen_paper_step4_back"):
            st.session_state.hust_gen_paper_step = 3
            st.rerun()
    with col2:
        if st.button("重新开始", key="hust_gen_paper_step4_restart"):
            reset_to_defaults()
            st.rerun()
    
    # 显示最终生成的文章
    st.subheader("生成的文章内容")
    st.text_area(
        "文章内容", 
        value=st.session_state.hust_gen_paper_final_text,
        height=500,
        key="hust_gen_paper_final_text_display",
        label_visibility="collapsed"
    )
    
    # 下载按钮
    st.download_button(
        label="下载文章",
        data=st.session_state.hust_gen_paper_final_text,
        file_name=f"{st.session_state.hust_gen_paper_theme}_文章.txt",
        mime="text/plain"
    )

    # 新增：历史记录部分
    st.divider()
    st.subheader("历史记录")
    
    # 获取所有缓存文件
    cache_dir = os.path.join(file_dir, 'llm_cache')
    if os.path.exists(cache_dir):
        cache_files = [f for f in os.listdir(cache_dir) if f.endswith('.pkl.gz')]
        cache_files.sort(key=lambda x: os.path.getmtime(os.path.join(cache_dir, x)), reverse=True)
        
        if cache_files:
            # 默认显示5条记录
            show_all = st.checkbox("显示所有历史记录", key="show_all_history")
            
            # 根据选择决定显示的数量
            display_files = cache_files if show_all else cache_files[:5]
            
            st.write(f"显示 {'所有' if show_all else '最近'} 生成的文章:")
            for i, cache_file in enumerate(display_files):
                cache_key = cache_file.replace('.pkl.gz', '')
                try:
                    # 读取缓存数据
                    filepath = os.path.join(cache_dir, cache_file)
                    with gzip.open(filepath, 'rb') as f:
                        cached_data = pickle.load(f)
                    
                    # 显示历史记录摘要
                    with st.expander(f"历史记录 {i+1} - {cache_key[:20]}..."):
                        st.write(f"生成时间: {time.ctime(os.path.getmtime(filepath))}")
                        st.text_area(
                            f"内容预览 {i+1}",
                            value=cached_data[:500] + ("..." if len(cached_data) > 500 else ""),
                            height=150,
                            key=f"history_preview_{i}",
                            label_visibility="collapsed"
                        )
                        
                        # 恢复按钮
                        if st.button(f"恢复此版本 {i+1}", key=f"restore_{i}"):
                            st.session_state.hust_gen_paper_final_text = cached_data
                            st.rerun()
                            
                        # 删除按钮
                        if st.button(f"删除此记录 {i+1}", key=f"delete_{i}"):
                            os.remove(filepath)
                            st.rerun()
                except Exception as e:
                    if DEBUG:
                        st.error(f"读取缓存文件 {cache_file} 失败: {str(e)}")
        else:
            st.write("暂无历史记录")
    else:
        st.write("暂无历史记录")

# 要求管理
def render_requirements_management():
    st.sidebar.header("生成要求管理")
    
    # 初始化多选状态（如果不存在）
    if 'hust_req_selected' not in st.session_state:
        st.session_state.hust_req_selected = [True] * len(st.session_state.hust_gen_paper_requirements)
    
    # 恢复默认按钮
    if st.sidebar.button("🔄 恢复默认要求", key="hust_gen_paper_reset_requirements"):
        st.session_state.hust_gen_paper_requirements = DEFAULT_REQUIREMENTS.copy()
        st.session_state.hust_req_selected = [True] * len(DEFAULT_REQUIREMENTS)  # 默认全部选中
        save_to_local_cache()
        st.rerun()
    
    # 多选编辑区域
    st.sidebar.markdown("**启用/禁用要求**")
    active_requirements = []
    
    for i, (req, is_selected) in enumerate(zip(st.session_state.hust_gen_paper_requirements, 
                                             st.session_state.hust_req_selected)):
        col1, col2 = st.sidebar.columns([1, 20])
        with col1:
            # 多选框（状态变化时自动保存）
            checked = st.checkbox(
                "选择要求", 
                value=is_selected,
                key=f"hust_req_check_{i}",
                label_visibility="collapsed",
                on_change=lambda i=i: (
                    st.session_state.hust_req_selected.__setitem__(i, st.session_state[f"hust_req_check_{i}"]),
                    save_to_local_cache()
                )
            )
        
        with col2:
            # 可折叠的编辑区域
            with st.expander(f"要求 {i+1}", expanded=checked):
                new_req = st.text_area(
                    "要求", 
                    value=req,
                    key=f"hust_gen_paper_req_{i}",
                    height=100,
                    label_visibility="collapsed",
                    on_change=lambda i=i: (
                        st.session_state.hust_gen_paper_requirements.__setitem__(i, st.session_state[f"hust_gen_paper_req_{i}"]),
                        save_to_local_cache()
                    )
                )
        
        if checked:
            active_requirements.append(req)
    
    # 按钮区域
    col_add, col_del = st.sidebar.columns(2)
    with col_add:
        if st.button("➕ 添加要求", key="hust_gen_paper_add_req"):
            st.session_state.hust_gen_paper_requirements.append("")
            st.session_state.hust_req_selected.append(True)  # 新要求默认选中
            save_to_local_cache()
            st.rerun()
    
    with col_del:
        if len(st.session_state.hust_gen_paper_requirements) > 0:
            if st.button("✖ 删除最后一项", key="hust_gen_paper_remove_req"):
                st.session_state.hust_gen_paper_requirements.pop()
                st.session_state.hust_req_selected.pop()
                save_to_local_cache()
                st.rerun()
    
    # 保存当前激活的要求到独立session状态
    st.session_state.active_requirements = active_requirements

# 主函数
def main():
    # 设置页面配置
    st.set_page_config(
        page_title="HUST 文章生成器",
        page_icon="📝",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # 自定义CSS样式
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
    
    # 初始化session state
    init_session_state()
    load_from_local_cache()
    
    # 渲染要求管理侧边栏
    render_requirements_management()

    # 根据步骤渲染不同内容
    if st.session_state.hust_gen_paper_step == 1:
        render_step1()
    elif st.session_state.hust_gen_paper_step == 2:
        render_step2()
    elif st.session_state.hust_gen_paper_step == 3:
        render_step3()
    elif st.session_state.hust_gen_paper_step == 4:
        render_step4()

if __name__ == "__main__":
    main()