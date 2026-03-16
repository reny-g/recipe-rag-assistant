"""
DashScope API 嵌入类 - 使用阿里云 DashScope 的文本嵌入服务
"""
import os
import logging
from typing import List

from langchain_community.embeddings import OpenAIEmbeddings
from langchain_core.embeddings import Embeddings

logger = logging.getLogger(__name__)


class DashScopeEmbeddings(Embeddings):
    """使用 DashScope API 的文本嵌入服务"""

    def __init__(
        self,
        api_key: str = None,
        base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
        model: str = "text-embedding-v3",
    ):
        """
        初始化 DashScope 嵌入

        Args:
            api_key: DashScope API key
            base_url: API base URL
            model: 嵌入模型名称
        """
        # 从环境变量获取 API key
        if not api_key:
            api_key = (
                os.getenv("DASHSCOPE_API_KEY")
                or os.getenv("QWEN_API_KEY")
                or os.getenv("OPENAI_API_KEY")
            )

        if not api_key:
            raise ValueError(
                "未找到 API key！请设置 DASHSCOPE_API_KEY 或 QWEN_API_KEY 环境变量"
            )

        self.api_key = api_key
        self.base_url = base_url
        self.model = model

        # 使用 OpenAI 兼容接口
        logger.info(f"初始化 DashScope 嵌入模型: {model}")
        print(f"  └─ 初始化 DashScope 嵌入: {model}")

        self.client = OpenAIEmbeddings(
            api_key=api_key,
            base_url=base_url,
            model=model,
        )

        logger.info("DashScope 嵌入初始化完成")
        print(f"  └─ DashScope 嵌入初始化完成")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        嵌入多个文档

        Args:
            texts: 文本列表

        Returns:
            嵌入向量列表
        """
        try:
            embeddings = self.client.embed_documents(texts)
            return embeddings
        except Exception as e:
            logger.error(f"文档嵌入失败: {e}")
            raise

    def embed_query(self, text: str) -> List[float]:
        """
        嵌入查询文本

        Args:
            text: 查询文本

        Returns:
            嵌入向量
        """
        try:
            embedding = self.client.embed_query(text)
            return embedding
        except Exception as e:
            logger.error(f"查询嵌入失败: {e}")
            raise
