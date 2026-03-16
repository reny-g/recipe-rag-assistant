import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, List

from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter


logger = logging.getLogger(__name__)


class DataPreparation:
    """加载食谱文档，并维护父文档与子块之间的映射关系。"""

    CATEGORY_MAPPING = {
        "meat_dish": "荤菜",
        "vegetable_dish": "素菜",
        "soup": "汤品",
        "dessert": "甜品",
        "breakfast": "早餐",
        "staple": "主食",
        "aquatic": "水产",
        "condiment": "调料",
        "drink": "饮品",
    }
    DIFFICULTY_LABELS = ["非常简单", "简单", "中等", "困难", "非常困难"]

    def __init__(self, data_path: str):
        self.data_path = Path(data_path)
        self.documents: List[Document] = []
        self.chunks: List[Document] = []
        self.parent_docs: Dict[str, Document] = {}

    def load_documents(self) -> List[Document]:
        """递归加载 markdown 文件，并补齐检索需要的 metadata。"""
        if not self.data_path.exists():
            raise FileNotFoundError(f"数据路径不存在: {self.data_path}")

        documents: List[Document] = []
        for file_path in sorted(self.data_path.rglob("*.md")):
            content = file_path.read_text(encoding="utf-8")
            # parent_id 基于稳定路径生成，避免每次启动都换成新的随机 ID。
            parent_id = self._build_parent_id(file_path)
            # content_hash 用来判断“文档内容是否变化”，即使 chunk 数量没变也能识别。
            content_hash = self._build_content_hash(content)
            doc = Document(
                page_content=content,
                metadata={
                    "source": str(file_path),
                    "parent_id": parent_id,
                    "content_hash": content_hash,
                    "doc_type": "parent",
                    "dish_name": file_path.stem,
                    "category": self._infer_category(file_path),
                    "difficulty": self._infer_difficulty(content),
                },
            )
            documents.append(doc)

        self.documents = documents
        self.parent_docs = {
            doc.metadata["parent_id"]: doc for doc in self.documents if "parent_id" in doc.metadata
        }
        logger.info("Loaded %s source documents from %s", len(self.documents), self.data_path)
        return self.documents

    def split_into_chunks(self) -> List[Document]:
        """按 Markdown 标题切块，尽量保留原始结构。"""
        if not self.documents:
            raise ValueError("请先加载文档。")

        splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[
                ("#", "h1"),
                ("##", "h2"),
                ("###", "h3"),
            ],
            strip_headers=False,
        )

        chunks: List[Document] = []
        for parent in self.documents:
            parent_id = parent.metadata["parent_id"]
            split_docs = splitter.split_text(parent.page_content) or [
                Document(page_content=parent.page_content, metadata={})
            ]

            for index, chunk in enumerate(split_docs):
                # 子块继承父文档 metadata，后续命中子块后才能回溯到完整文档。
                chunk.metadata.update(parent.metadata)
                chunk.metadata.update(
                    {
                        "doc_type": "child",
                        # chunk_id 同样保持稳定，便于兼容性检查和日志排查。
                        "chunk_id": self._build_chunk_id(parent_id, index),
                        "chunk_index": index,
                        "chunk_size": len(chunk.page_content),
                        "parent_id": parent_id,
                    }
                )
                chunks.append(chunk)

        self.chunks = chunks
        logger.info("Split %s documents into %s chunks", len(self.documents), len(self.chunks))
        return self.chunks

    def chunk_documents(self) -> List[Document]:
        return self.split_into_chunks()

    def get_parent_documents(self, chunks: List[Document]) -> List[Document]:
        """根据命中的子块回溯父文档，并去重。"""
        seen_parent_ids = set()
        parent_docs: List[Document] = []

        for chunk in chunks:
            parent_id = chunk.metadata.get("parent_id")
            if not parent_id or parent_id in seen_parent_ids:
                continue
            parent = self.parent_docs.get(parent_id)
            if parent is not None:
                seen_parent_ids.add(parent_id)
                parent_docs.append(parent)

        return parent_docs

    def get_statistics(self) -> Dict[str, Any]:
        """返回当前知识库的统计信息。"""
        if not self.documents:
            return {}

        categories: Dict[str, int] = {}
        difficulties: Dict[str, int] = {}

        for doc in self.documents:
            category = doc.metadata.get("category", "未知")
            difficulty = doc.metadata.get("difficulty", "未知")
            categories[category] = categories.get(category, 0) + 1
            difficulties[difficulty] = difficulties.get(difficulty, 0) + 1

        average_chunk_size = 0.0
        if self.chunks:
            total_size = sum(chunk.metadata.get("chunk_size", 0) for chunk in self.chunks)
            average_chunk_size = total_size / len(self.chunks)

        return {
            "total_documents": len(self.documents),
            "total_chunks": len(self.chunks),
            "categories": categories,
            "difficulties": difficulties,
            "avg_chunk_size": average_chunk_size,
        }

    @classmethod
    def get_supported_categories(cls) -> List[str]:
        return list(cls.CATEGORY_MAPPING.values())

    @classmethod
    def get_supported_difficulties(cls) -> List[str]:
        return list(cls.DIFFICULTY_LABELS)

    def _infer_category(self, file_path: Path) -> str:
        path_parts = set(file_path.parts)
        for key, label in self.CATEGORY_MAPPING.items():
            if key in path_parts:
                return label
        return "其他"

    def _infer_difficulty(self, content: str) -> str:
        if "★★★★" in content or "★★★★★" in content:
            return "非常困难"
        if "★★★" in content:
            return "困难"
        if "★★" in content:
            return "中等"
        if "★" in content:
            return "简单"
        return "未知"

    def _build_parent_id(self, file_path: Path) -> str:
        try:
            stable_path = file_path.relative_to(self.data_path)
        except ValueError:
            stable_path = file_path
        digest = hashlib.md5(str(stable_path).encode("utf-8")).hexdigest()
        return f"parent-{digest}"

    def _build_chunk_id(self, parent_id: str, index: int) -> str:
        return f"{parent_id}-chunk-{index}"

    def _build_content_hash(self, content: str) -> str:
        return hashlib.md5(content.encode("utf-8")).hexdigest()
