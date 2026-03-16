import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_DATA_PATH = PROJECT_ROOT / "data"
DEFAULT_INDEX_PATH = PROJECT_ROOT / "vector_index"
ENV_PATHS = [
    PROJECT_ROOT / ".env",
    PROJECT_ROOT.parent / ".env",
]


answer_system_prompt = """
你是一名专业的中文菜谱问答助手。请严格依据提供的菜谱上下文回答用户问题。

回答要求：
- 优先使用上下文中的事实，不要编造不存在的菜谱、步骤、食材或时间。
- 如果上下文不足以回答，就明确说明“知识库中没有足够信息”。
- 如果用户是在追问上一轮内容，要结合对话历史理解指代对象。
- 如果用户的问题本身缺少明确对象，例如“这个菜”“上一个菜”“要多久”，而上下文也不足，请先要求用户说明具体菜名。
- 回答尽量使用中文，清晰、直接、可操作。
- 不要列出与当前问题无关的其他菜谱作为补充。

已检索到的相关菜谱信息：
{context}
""".strip()


contextualize_system_prompt = """
你是一个中文多轮检索改写助手。请结合最近的对话历史，把当前用户问题改写成适合检索的完整问题。

要求：
- 如果当前问题已经完整，直接返回原问题。
- 如果当前问题包含“这个”“那个”“上一个菜”“继续说”“要多久”“怎么做”等指代或省略，补全它指向的具体菜名或对象。
- 只返回改写后的最终检索问题，不要解释。
""".strip()


@dataclass
class RAGConfig:
    data_path: str = str(DEFAULT_DATA_PATH)
    index_save_path: str = str(DEFAULT_INDEX_PATH)
    embedding_model: str = "BAAI/bge-small-zh-v1.5"
    use_api_embeddings: bool = False
    embedding_device: str = "cpu"
    embedding_local_files_only: bool = True
    llm_model: str = "qwen3.5-plus"
    enable_thinking: bool = False
    temperature: float = 0.2
    max_tokens: int = 2048
    contextualize_timeout: float = 8.0
    answer_timeout: float = 45.0
    contextualize_max_retries: int = 0
    answer_max_retries: int = 1
    top_k: int = 5
    history_window: int = 4


DEFAULT_CONFIG = RAGConfig()


def load_project_env() -> None:
    for env_path in ENV_PATHS:
        if env_path.exists():
            load_dotenv(env_path, override=False)


def resolve_llm_credentials(model_name: str) -> Tuple[str, Optional[str]]:
    api_key = (
        os.getenv("OPENAI_API_KEY")
        or os.getenv("DASHSCOPE_API_KEY")
        or os.getenv("QWEN_API_KEY")
    )
    base_url = (
        os.getenv("OPENAI_BASE_URL")
        or os.getenv("DASHSCOPE_BASE_URL")
        or os.getenv("QWEN_BASE_URL")
    )

    if not base_url and "qwen" in model_name.lower():
        base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    return api_key or "", base_url
