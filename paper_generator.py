import streamlit as st
from app import AppFramework
from typing import List, Dict
import os
import time
import gzip
import pickle

DEBUG = False

from agent import agent

# 大模型接口调用函数
def generate_result(prompt: str) -> str:
    """
    本地的大模型接口调用
    """
    return agent.simple_request(prompt)

def generate_prompt(prompt: str, requirements: List[str]) -> str:
    """生成prompt"""
    return f"原始文本：\n{prompt}\n\n修改要求如下:\n" + "\n".join(requirements)

# 默认要求
DEFAULT_REQUIREMENTS = [
    "请帮我适当缩短文本篇幅，保证可阅读性，并将术语更加易懂化或减少，保证大一新生也能读懂，但不改变原有的结构和严谨性，并且不使用任何比喻、类比的修辞手法，保证文本的严肃性。",
    "我希望你能保留{主题}相关的内容，因为我这个内容用意是介绍{主题}。"
]

class PaperGeneratorPage:
    def __init__(self):
        self.cache_dir = os.path.join(os.path.dirname(__file__), 'llm_cache')
        self.init_session_state()
        self.load_from_local_cache()

    def load_from_local_cache(self):
        """从缓存加载数据（完整实现）"""        
        # 防止重复加载的标记
        if '_cache_loaded' not in st.session_state:
            st.session_state._cache_loaded = False
        
        # 如果已经加载过则跳过
        if st.session_state._cache_loaded:
            # 跳过重复加载
            return

        cached_data = AppFramework.load_from_local_cache()
            
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
        
    def init_session_state(self):
        """初始化会话状态"""
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
        if 'hust_req_selected' not in st.session_state:
            st.session_state.hust_req_selected = [True] * len(DEFAULT_REQUIREMENTS)
    
    # 业务逻辑函数
    def update_theme(self, new_theme):
        """更新主题"""
        st.session_state.hust_gen_paper_theme = new_theme
        AppFramework.save_to_local_cache(self.get_session_data())

    def update_outlines(self, new_outlines):
        """更新大纲"""
        st.session_state.hust_gen_paper_outlines_text = new_outlines
        AppFramework.save_to_local_cache(self.get_session_data())

    def update_prompt(self, new_prompt):
        """更新提示词"""
        st.session_state.hust_gen_paper_generated_text = new_prompt
        AppFramework.save_to_local_cache(self.get_session_data())

    def reset_to_defaults(self):
        """重置为默认设置"""
        st.session_state.hust_gen_paper_theme = ""
        st.session_state.hust_gen_paper_outlines = []
        st.session_state.hust_gen_paper_references = []
        st.session_state.hust_gen_paper_requirements = DEFAULT_REQUIREMENTS.copy()
        st.session_state.hust_gen_paper_outlines_text = ""
        st.session_state.hust_gen_paper_generated_text = ""
        st.session_state.hust_gen_paper_final_text = ""
        st.session_state.hust_gen_paper_step = 1
        st.session_state.hust_req_selected = [True] * len(DEFAULT_REQUIREMENTS)
        AppFramework.save_to_local_cache(self.get_session_data())

    # 渲染函数
    def render_step1(self):
        """第一步：输入主题和大纲"""
        st.header("1. 输入主题和大纲")
        
        if st.button("🔄 恢复默认设置", key="hust_gen_paper_reset_defaults"):
            self.reset_to_defaults()
        
        theme = st.text_input(
            "文章主题", 
            value=st.session_state.hust_gen_paper_theme,
            key="hust_gen_paper_theme_input",
            placeholder="请输入文章主题，例如：人工智能的发展历史",
            on_change=lambda: self.update_theme(st.session_state.hust_gen_paper_theme_input)
        )
        
        outlines_text = st.text_area(
            "文章大纲（每行一个要点）", 
            value=st.session_state.hust_gen_paper_outlines_text,
            key="hust_gen_paper_outlines_input",
            height=300,
            placeholder="请输入文章大纲，每行一个要点。例如：\n1. 人工智能的定义\n2. 人工智能的发展阶段\n3. 当前人工智能的应用领域",
            on_change=lambda: self.update_outlines(st.session_state.hust_gen_paper_outlines_input)
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
            AppFramework.save_to_local_cache(self.get_session_data())
            st.rerun()

    def render_step2(self):
        """第二步：输入参考文本"""
        st.header("2. 输入参考文本")
        st.write("参考文本太复杂的时候，建议找个网页大模型，用网页大模型回炉重造一下参考文本，提示词可以用'概括一下是什么研究，我要作为参考文献引入的：'。")
        st.write(f"主题: {st.session_state.hust_gen_paper_theme}")
        
        if st.button("返回上一步", key="hust_gen_paper_step2_back"):
            st.session_state.hust_gen_paper_step = 1
            AppFramework.save_to_local_cache(self.get_session_data())
            st.rerun()
        
        for i, outline in enumerate(st.session_state.hust_gen_paper_outlines):
            st.subheader(f"大纲要点 {i+1}")
            st.write(outline)
            
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
                    AppFramework.save_to_local_cache(self.get_session_data())
                )
            )
        
        if st.button("生成文章", key="hust_gen_paper_generate"):
            prompt = f"{st.session_state.hust_gen_paper_theme}\n"
            for outline, reference in zip(st.session_state.hust_gen_paper_outlines, st.session_state.hust_gen_paper_references):
                prompt += f"{outline}\n"
                if reference:
                    prompt += f"  {reference}\n"
            
            selected_requirements = []
            order = 1
            for i, (req, is_selected) in enumerate(zip(st.session_state.hust_gen_paper_requirements, 
                                                     st.session_state.hust_req_selected), 1):
                if is_selected:
                    processed_req = req.replace("{主题}", st.session_state.hust_gen_paper_theme)
                    selected_requirements.append(f"{order}. {processed_req}")
                    order += 1
            
            with st.spinner("正在生成提示词，请稍候..."):
                generated_text = generate_prompt(prompt, selected_requirements)
            
            st.session_state.hust_gen_paper_generated_text = generated_text
            st.session_state.hust_gen_paper_step = 3
            AppFramework.save_to_local_cache(self.get_session_data())
            st.rerun()

    def render_step3(self):
        """第三步：显示提示词并生成文章"""
        st.header("3. 提示词生成")
        st.write(f"主题: {st.session_state.hust_gen_paper_theme}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("返回修改参考文本", key="hust_gen_paper_step3_back"):
                st.session_state.hust_gen_paper_step = 2
                st.rerun()
        with col2:
            if st.button("重新开始", key="hust_gen_paper_step3_restart"):
                self.reset_to_defaults()
                st.rerun()
        
        st.subheader("生成的提示词内容")
        st.text_area(
            "提示词内容", 
            value=st.session_state.hust_gen_paper_generated_text,
            height=500,
            key="hust_gen_paper_generated_text_display",
            label_visibility="collapsed",
            on_change=lambda: self.update_prompt(st.session_state.hust_gen_paper_generated_text_display)
        )
        
        if st.button("生成最终文章", key="hust_gen_paper_generate_final"):
            with st.spinner("正在生成文章，请稍候..."):
                cache_key, final_text = generate_result(st.session_state.hust_gen_paper_generated_text_display)
                # 记录一下对应的prompt为.pkl.gz
                with gzip.open(os.path.join(self.cache_dir, cache_key + '.pkl.gz.prompt'), 'wb') as f:
                    pickle.dump(st.session_state.hust_gen_paper_generated_text, f)
            
            st.session_state.hust_gen_paper_final_text = final_text
            st.session_state.hust_gen_paper_step = 4
            AppFramework.save_to_local_cache(self.get_session_data())
            st.rerun()
        
        self.render_history('prompt')

    def render_step4(self):
        """第四步：显示最终生成的文章"""
        st.header("4. 文章生成结果")
        st.write(f"主题: {st.session_state.hust_gen_paper_theme}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("返回修改提示词", key="hust_gen_paper_step4_back"):
                st.session_state.hust_gen_paper_step = 3
                st.rerun()
        with col2:
            if st.button("重新开始", key="hust_gen_paper_step4_restart"):
                self.reset_to_defaults()
                st.rerun()
        
        st.subheader("生成的文章内容")
        st.text_area(
            "文章内容", 
            value=st.session_state.hust_gen_paper_final_text,
            height=500,
            key="hust_gen_paper_final_text_display",
            label_visibility="collapsed"
        )
        
        st.download_button(
            label="下载文章",
            data=st.session_state.hust_gen_paper_final_text,
            file_name=f"{st.session_state.hust_gen_paper_theme}_文章.txt",
            mime="text/plain"
        )

        self.render_history()

    def render_history(self, history_type='response'):
        st.divider()
        st.subheader("历史记录")
        
        cache_files = AppFramework.load_history(self.cache_dir)
        back_str = '.pkl.gz'
        if history_type == 'prompt':
            back_str += '.prompt'
        cache_files = [cache_file for cache_file in cache_files if cache_file.endswith(back_str)]
        if cache_files:
            show_all = st.checkbox("显示所有历史记录", key="show_all_history")
            display_files = cache_files if show_all else cache_files[:5]
            
            st.write(f"显示 {'所有' if show_all else '最近'} 生成的文章:")
            for i, cache_file in enumerate(display_files):
                cache_key = cache_file.replace(back_str, '')
                try:
                    filepath = os.path.join(self.cache_dir, cache_file)
                    with gzip.open(filepath, 'rb') as f:
                        cached_data = pickle.load(f)
                    
                    with st.expander(f"历史记录 {i+1} - {cache_key[:20]}..."):
                        st.write(f"生成时间: {time.ctime(os.path.getmtime(filepath))}")
                        st.text_area(
                            f"内容预览 {i+1}",
                            value=cached_data[:500] + ("..." if len(cached_data) > 500 else ""),
                            height=150,
                            key=f"history_preview_{i}",
                            label_visibility="collapsed"
                        )
                        
                        if st.button(f"恢复此版本 {i+1}", key=f"restore_{i}"):
                            st.session_state.hust_gen_paper_final_text = cached_data
                            st.rerun()
                            
                        if st.button(f"删除此记录 {i+1}", key=f"delete_{i}"):
                            os.remove(filepath)
                            st.rerun()
                except Exception as e:
                    if st.session_state.get('DEBUG', False):
                        st.error(f"读取缓存文件 {cache_file} 失败: {str(e)}")
        else:
            st.write("暂无历史记录")

    def render_requirements_management(self):
        """渲染要求管理侧边栏"""
        st.sidebar.header("生成要求管理")
        
        if st.sidebar.button("🔄 恢复默认要求"):
            st.session_state.hust_gen_paper_requirements = DEFAULT_REQUIREMENTS.copy()
            st.session_state.hust_req_selected = [True] * len(DEFAULT_REQUIREMENTS)
            AppFramework.save_to_local_cache(self.get_session_data())
            
        st.sidebar.markdown("**启用/禁用要求**")
        for i, (req, is_selected) in enumerate(zip(st.session_state.hust_gen_paper_requirements, 
                                                st.session_state.hust_req_selected)):
            col1, col2 = st.sidebar.columns([1, 20])
            with col1:
                checked = st.checkbox(
                    "选择要求", 
                    value=is_selected,
                    key=f"hust_req_check_{i}",
                    label_visibility="collapsed",
                    on_change=lambda i=i: (
                        st.session_state.hust_req_selected.__setitem__(i, st.session_state[f"hust_req_check_{i}"]),
                        AppFramework.save_to_local_cache(self.get_session_data())
                    )
                )
            
            with col2:
                with st.expander(f"要求 {i+1}", expanded=checked):
                    new_req = st.text_area(
                        "要求", 
                        value=req,
                        key=f"hust_gen_paper_req_{i}",
                        height=100,
                        label_visibility="collapsed",
                        on_change=lambda i=i: (
                            st.session_state.hust_gen_paper_requirements.__setitem__(i, st.session_state[f"hust_gen_paper_req_{i}"]),
                            AppFramework.save_to_local_cache(self.get_session_data())
                        )
                    )
        
        col_add, col_del = st.sidebar.columns(2)
        with col_add:
            if st.button("➕ 添加要求"):
                st.session_state.hust_gen_paper_requirements.append("")
                st.session_state.hust_req_selected.append(True)
                AppFramework.save_to_local_cache(self.get_session_data())
        
        with col_del:
            if len(st.session_state.hust_gen_paper_requirements) > 0 and st.button("✖ 删除最后一项"):
                st.session_state.hust_gen_paper_requirements.pop()
                st.session_state.hust_req_selected.pop()
                AppFramework.save_to_local_cache(self.get_session_data())

    def get_session_data(self) -> Dict:
        """获取当前会话数据"""
        return {
            'theme': st.session_state.hust_gen_paper_theme,
            'outlines': st.session_state.hust_gen_paper_outlines,
            'references': st.session_state.hust_gen_paper_references,
            'requirements': st.session_state.hust_gen_paper_requirements,
            'outlines_text': st.session_state.hust_gen_paper_outlines_text,
            'req_selected': st.session_state.hust_req_selected,
            'generated_text': st.session_state.hust_gen_paper_generated_text,
            'final_text': st.session_state.hust_gen_paper_final_text
        }

    def render(self):
        """渲染整个页面"""
        self.render_requirements_management()
        
        if st.session_state.hust_gen_paper_step == 1:
            self.render_step1()
        elif st.session_state.hust_gen_paper_step == 2:
            self.render_step2()
        elif st.session_state.hust_gen_paper_step == 3:
            self.render_step3()
        elif st.session_state.hust_gen_paper_step == 4:
            self.render_step4()