"""
Usage: Extract text and tables from PDF files using pdfplumber and pandas
Dependencies: pdfplumber, pandas, openpyxl, tabulate
Export: LLMAgent class
Methods:
    - init_llm: Initialize the LLM model
    - choose_model: Choose the model type
    - simple_request: Simple request to the LLM
https://python.langchain.com/docs/integrations/text_embedding/
"""

def set_proxy():
    # Set the proxy URL and port
    proxy_url = 'http://127.0.0.1'
    proxy_port = '10809'
    # Set the http_proxy and https_proxy environment variables
    os.environ['http_proxy'] = f'{proxy_url}:{proxy_port}'
    os.environ['https_proxy'] = f'{proxy_url}:{proxy_port}'

import os
import re
file_dir = os.path.dirname(__file__)
    
# 调试模式下可以控制打印prompt模板和变量
DEBUG_MODE = False

DEFAULT_MODEL = "qwq:latest-fixed"
model_options = {
    "gpt": ["gpt-4o", "gpt-4-1106-preview", "deepseek-chat", "gpt-4o-all", "gpt-4.1"],
    "claude": ["claude-3-7-sonnet-20250219", "claude-3-sonnet-20240229", "claude-3-7-sonnet-latest", "claude-3-5-sonnet-20241022", "claude-3-5-sonnet-20240620"],
    "gemini": ["gemini-2.0-pro", "gemini-2.0-flash", "gemini-2.5-pro", "gemini-2.5-flash"],
    "llama2": ["llama2:7b", "llama2:70b", "llama2:13b", "llama2-chinese:13b", "qwq:latest-fixed"],
    "baidu": ["baidu"]
}

# embedding_model = "openai"
embedding_model = "default"

def choose_actual_model(model):
    # get all the models of model options
    all_models = [model for models in model_options.values() for model in models]
    if model in all_models:
        return model
    elif model not in model_options:
        print("Invalid model type")
        exit(1)
    model_list = model_options[model]
    print("Choose the model:")
    for i, model in enumerate(model_list):
        print(f"{i+1}: {model}")
    model_type = int(input()) - 1
    if model_type < 0 or model_type >= len(model_list):
        print("Invalid model")
        exit(1)
    return model_list[model_type]

def create_llm(model, temperature):
    # 调用选择实际模型的函数
    actual_model = choose_actual_model(model)

    # 如果选择的是 Llama2 模型
    if 'llama2' in model or "qwq" in model:
        from langchain_ollama import OllamaLLM
        from langchain_ollama import OllamaEmbeddings

        # 初始化 Llama2 模型
        llm = OllamaLLM(model=actual_model, temperature=temperature)
        # 初始化嵌入模型
        embeddings = OllamaEmbeddings(model=actual_model)

    # 如果选择的是 GPT 模型或 deepseek-chat 模型
    elif 'gpt' in model or 'deepseek' in model or 'claude' in model:
        from langchain_openai import ChatOpenAI
        from dotenv import load_dotenv

        # 加载 .env 文件
        load_dotenv(override=True)

        # 初始化默认参数
        base_url = os.getenv("CHAT_MODEL_URL")
        max_tokens = 8192  # 默认对 OpenAI 模型限制 token
        api_key_name = "OPENAI_API_KEY"

        # 如果是 deepseek-chat 模型，特殊处理
        if actual_model == "deepseek-chat":
            api_key_name = "DEEPSEEK_API_KEY"
            base_url = os.getenv("CHAT_MODEL_URL")
            max_tokens = 8192  # 设置 deepseek-chat 的最大 token 限制
        # 从环境变量中获取 API 密钥
        api_key = os.getenv(api_key_name)
        if not api_key:
            print(f"Error: {api_key_name} is not set in the .env file or environment variables.")
            exit(1)

        # 初始化 OpenAI 或 Deepseek 的 Chat 模型
        llm = ChatOpenAI(
            temperature=temperature,
            max_tokens=max_tokens,
            model=actual_model,
            openai_api_key=api_key,
            openai_api_base=base_url
        )
        # 初始化嵌入模型
        if embedding_model == "default":
            # BAAI/bge-m3
            # pip install --upgrade --quiet  sentence_transformers
            # pip install -U FlagEmbedding
            # pip install langchain-huggingface
            # export HF_ENDPOINT=https://hf-mirror.com
            from langchain_huggingface import HuggingFaceEmbeddings
            model_name = "BAAI/bge-small-en-v1.5"
            # model_name = "BAAI/bge-large-en-v1.5"
            embeddings = HuggingFaceEmbeddings(
                cache_folder=os.path.join(file_dir, "cache"),
                model_name=model_name)
        else:
            from langchain_openai import OpenAIEmbeddings
            model_name = "text-embedding-ada-002"
            embeddings = OpenAIEmbeddings(
                model=model_name,
                openai_api_key=os.getenv("EMBEDDING_API_KEY"),
                openai_api_base=os.getenv("EMBEDDING_MODEL_URL")
            )
    elif 'gemini' in model:
        from langchain_google_genai import ChatGoogleGenerativeAI
        from dotenv import load_dotenv

        load_dotenv(override=True)
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("Error: GEMINI_API_KEY is not set in the .env file or environment variables.")
            exit(1)

        llm = ChatGoogleGenerativeAI(
            model=actual_model,
            temperature=temperature,
            google_api_key=api_key
        )
        embeddings = None  # Gemini暂不支持embedding
    else:
        print("Error: Unsupported model type.")
        exit(1)

    # 返回语言模型和嵌入模型
    return llm, embeddings

import hashlib
import json
import gzip
import pickle


class LLMAgent:
    def __init__(self, model=DEFAULT_MODEL, temperature=0, init=True):
        self.model = model
        self.temperature = temperature
        self.llm = None  # 改为实例变量，避免线程间共享
        self.embeddings = None
        if init:
            self.init_llm()
        pass

    @staticmethod
    def _generate_cache_key(prompt_path, user_context, input, chat_history, top_k_retrieval, kwargs,
                            return_retrieved_content):
        """生成唯一的缓存键"""
        params = {
            'prompt_path': prompt_path,
            'user_context': user_context,
            'input': input,
            'chat_history': chat_history,
            'top_k_retrieval': top_k_retrieval,
            'kwargs': kwargs,
            'return_retrieved_content': return_retrieved_content
        }
        # 转换为JSON字符串并排序键
        params_str = json.dumps(params, sort_keys=True, ensure_ascii=False).encode('utf-8')
        return hashlib.md5(params_str).hexdigest()

    @staticmethod
    def _load_from_cache(cache_key):
        """从缓存加载"""
        cache_dir = os.path.join(file_dir, 'llm_cache')
        filepath = os.path.join(cache_dir, f"{cache_key}.pkl.gz")

        if os.path.exists(filepath):
            try:
                with gzip.open(filepath, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"Error loading cache: {e}, removing invalid file")
                os.remove(filepath)
        return None

    @staticmethod
    def _save_to_cache(cache_key, data):
        """保存到缓存"""
        cache_dir = os.path.join(file_dir, 'llm_cache')
        os.makedirs(cache_dir, exist_ok=True)
        filepath = os.path.join(cache_dir, f"{cache_key}.pkl.gz")

        with gzip.open(filepath, 'wb') as f:
            pickle.dump(data, f)

    @staticmethod
    def _clean_cache(max_size=1000):
        """LRU缓存清理"""
        cache_dir = os.path.join(file_dir, 'llm_cache')
        files = [os.path.join(cache_dir, f) for f in os.listdir(cache_dir)]

        # 按最后访问时间排序
        files.sort(key=lambda x: os.path.getatime(x))

        # 删除最旧的超出部分
        while len(files) > max_size:
            os.remove(files.pop(0))

    def init_llm(self):
        self.llm, self.embeddings = create_llm(self.model, self.temperature)

    def choose_model(self, model=None, temperature=0, init=True):
        self.temperature = temperature
        if not model:
            model_type = int(input("Choose the model type (1: OpenAI, 2: Llama2): "))
            # Test OpenAI model
            if model_type == 1:
                set_proxy()
                self.model = "gpt"
            # Test Llama2 model
            elif model_type == 2:
                self.model = 'llama2'
            else:
                print("Invalid model type")
                exit(1)
        else:
            self.model = model
        if init:
            self.init_llm()

    @staticmethod
    def parse_llm_response(response):
        """
        Usage: Parse the response from the LLM model
        :param response: str, response from the LLM model
        :return: str, parsed response
        """
        from langchain_core.messages import AIMessage
        if type(response) == dict:
            if 'answer' in response:
                answer = response['answer']
            elif 'content' in response:
                answer = response['content']
            else:
                answer = response
        elif type(response) == type(AIMessage(content="")):
            answer = response.content
        else:
            answer = response

        return answer

    def simple_request(self, request_prompt, enable_cache=True):
        '''
        Usage: Request the LLM model to generate a response based on the prompt
        :param request_prompt: str, prompt for the LLM model
        :param enable_cache: bool, whether to enable caching
        :return: str, response from the LLM model
        '''
        # 生成缓存键时需要排除不影响结果的控制参数
        cache_key = hashlib.md5(request_prompt.encode('utf-8')).hexdigest()
        if enable_cache:
            # 尝试读取缓存
            cached = self._load_from_cache(cache_key=cache_key)
            if cached is not None:
                return cached
        # 确保LLM已经初始化
        if self.llm is None:
            self.init_llm()
            
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import StrOutputParser

        output_parser = StrOutputParser()

        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful AI assistant."),
            ("user", "{input}")
        ])
        chain = prompt | self.llm | output_parser

        response = chain.invoke({"input": request_prompt})

        response = self.parse_llm_response(response)

        # 在返回结果前保存缓存
        self._save_to_cache(cache_key, response)

        return cache_key, response

agent = LLMAgent(model=DEFAULT_MODEL, init=False)
# agent = LLMAgent(model=DEFAULT_MODEL, init=True)