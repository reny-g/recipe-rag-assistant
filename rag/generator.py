import logging
from typing import Dict, Generator, Iterable, List, Union

from langchain_core.documents import Document
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser

from config import answer_system_prompt, contextualize_system_prompt, resolve_llm_credentials

logger = logging.getLogger(__name__)

try:
    from langchain_openai import ChatOpenAI
except ImportError:  # pragma: no cover
    ChatOpenAI = None


class RagGenerator:
    """Wraps query contextualization and final grounded answer generation."""

    CONTEXTUALIZE_HINTS = (
        "它",
        "这个",
        "那个",
        "这道菜",
        "那道菜",
        "上一个",
        "上一道",
        "刚才",
        "前面",
        "继续说",
        "继续",
        "要多久",
        "多久",
        "怎么做",
        "怎么煮",
        "几分钟",
        "可以吗",
    )

    def __init__(
        self,
        model_name: str,
        enable_thinking: bool,
        temperature: float,
        max_tokens: int,
        contextualize_timeout: float = 8.0,
        answer_timeout: float = 45.0,
        contextualize_max_retries: int = 0,
        answer_max_retries: int = 1,
    ):
        self.model_name = model_name
        self.enable_thinking = enable_thinking
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.contextualize_timeout = contextualize_timeout
        self.answer_timeout = answer_timeout
        self.contextualize_max_retries = contextualize_max_retries
        self.answer_max_retries = answer_max_retries

        logger.info("Initializing generator module with model=%s", model_name)
        print(f"  └─ Initializing LLM: {model_name}")
        self.contextualize_model = self._setup_client(
            timeout=self.contextualize_timeout,
            max_retries=self.contextualize_max_retries,
        )
        self.answer_model = self._setup_client(
            timeout=self.answer_timeout,
            max_retries=self.answer_max_retries,
        )
        self.output_parser = StrOutputParser()
        print("  └─ LLM initialization complete")

    def contextualize_query(self, query: str, history: List[Dict[str, str]]) -> str:
        try:
            if not self._should_contextualize(query, history):
                return query

            history_messages = self._history_to_messages(history)
            messages: List[BaseMessage] = [SystemMessage(content=contextualize_system_prompt)]
            messages.extend(history_messages)
            messages.append(HumanMessage(content=f"当前问题：{query}"))
            return (self.contextualize_model | self.output_parser).invoke(messages).strip()
        except Exception as exc:
            logger.warning(
                "Query contextualization failed, fallback to original query: %s: %s",
                type(exc).__name__,
                exc,
            )
            return query

    def generate_answer(
        self,
        query: str,
        context_docs: List[Document],
        history: List[Dict[str, str]],
        stream: bool = False,
    ) -> Union[str, Generator[str, None, None]]:
        try:
            context = self._build_context(context_docs)
            messages: List[BaseMessage] = [
                SystemMessage(content=answer_system_prompt.format(context=context))
            ]
            messages.extend(self._history_to_messages(history))
            messages.append(HumanMessage(content=query))

            chain = self.answer_model | self.output_parser
            if stream:
                return chain.stream(messages)
            return chain.invoke(messages)
        except Exception as exc:
            logger.error("Answer generation failed: %s: %s", type(exc).__name__, exc)
            return f"抱歉，生成回答时出现错误：{exc}。请检查网络连接和 API 配置。"

    def is_context_dependent_query(self, query: str) -> bool:
        normalized_query = query.strip()
        if not normalized_query:
            return False
        if any(token in normalized_query for token in self.CONTEXTUALIZE_HINTS):
            return True
        return len(normalized_query) <= 4

    def _build_context(self, docs: Iterable[Document], max_length: int = 6000) -> str:
        docs = list(docs)
        if not docs:
            return "暂无相关菜谱信息。"

        parts: List[str] = []
        current_length = 0

        for index, doc in enumerate(docs, start=1):
            title = doc.metadata.get("dish_name", "未知菜品")
            category = doc.metadata.get("category", "未知分类")
            difficulty = doc.metadata.get("difficulty", "未知难度")
            block = (
                f"【菜谱 {index}】{title} | 分类: {category} | 难度: {difficulty}\n"
                f"{doc.page_content.strip()}\n"
            )
            if current_length + len(block) > max_length:
                break
            parts.append(block)
            current_length += len(block)

        return "\n" + ("=" * 50) + "\n".join(parts)

    def _history_to_messages(self, history: List[Dict[str, str]]) -> List[BaseMessage]:
        messages: List[BaseMessage] = []
        for item in history:
            content = item.get("content", "").strip()
            if not content:
                continue
            if item.get("role") == "user":
                messages.append(HumanMessage(content=content))
            elif item.get("role") == "assistant":
                messages.append(AIMessage(content=content))
        return messages

    def _should_contextualize(self, query: str, history: List[Dict[str, str]]) -> bool:
        if not history:
            return False

        normalized_query = query.strip()
        if not normalized_query:
            return False

        if any(token in normalized_query for token in self.CONTEXTUALIZE_HINTS):
            return True

        return len(normalized_query) <= 4

    def _setup_client(self, timeout: float, max_retries: int):
        if ChatOpenAI is None:
            raise ImportError("Missing dependency `langchain-openai`, cannot initialize LLM client.")

        api_key, base_url = resolve_llm_credentials(self.model_name)
        if not api_key:
            raise ValueError(
                "No API key found. Please set OPENAI_API_KEY, DASHSCOPE_API_KEY, or QWEN_API_KEY in `.env`."
            )

        return ChatOpenAI(
            api_key=api_key,
            base_url=base_url,
            model=self.model_name,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            timeout=timeout,
            max_retries=max_retries,
            extra_body={"enable_thinking": self.enable_thinking},
        )
