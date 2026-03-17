import logging
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List

from langchain_community.retrievers import BM25Retriever
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document


logger = logging.getLogger(__name__)


class HybridRetriever:
    """混合检索器：向量检索 + BM25，再用 RRF 重排。"""

    def __init__(self, vector_store: FAISS, chunks: List[Document], default_k: int = 5):
        self.vector_store = vector_store
        self.chunks = chunks
        self.default_k = default_k
        # 两路检索器共享同一批切块数据，最后统一合并排序。
        self.vector_retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": default_k},
        )
        self.bm25_retriever = BM25Retriever.from_documents(chunks, k=default_k)
        # 向量检索和 BM25 互不依赖，可以并行执行来减少等待。
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="hybrid-retriever")

    def hybrid_search(self, query: str, top_k: int = 5) -> List[Document]:
        """执行混合检索并返回最终重排后的结果。"""
        # 两路召回同时开始，最后再统一做 RRF 融合。
        vector_future = self._executor.submit(self.vector_retriever.invoke, query)
        bm25_future = self._executor.submit(self.bm25_retriever.invoke, query)
        vector_docs = vector_future.result()
        bm25_docs = bm25_future.result()
        reranked_docs = self._rrf_rerank(query, vector_docs, bm25_docs)
        logger.info("Retrieved %s reranked chunks for query=%r", len(reranked_docs), query)
        return reranked_docs[:top_k]

    def metadata_filtered_search(
        self,
        query: str,
        filters: Dict[str, Any],
        top_k: int = 5,
    ) -> List[Document]:
        """先召回，再按 metadata 做二次过滤。"""
        candidate_docs = self.hybrid_search(query, top_k=max(top_k * 3, top_k))
        filtered_docs: List[Document] = []

        for doc in candidate_docs:
            if self._matches_filters(doc, filters):
                filtered_docs.append(doc)
            if len(filtered_docs) >= top_k:
                break

        return filtered_docs

    def _matches_filters(self, doc: Document, filters: Dict[str, Any]) -> bool:
        for key, expected in filters.items():
            actual = doc.metadata.get(key)
            if isinstance(expected, list):
                if actual not in expected:
                    return False
            elif actual != expected:
                return False
        return True

    def _rrf_rerank(
        self,
        query: str,
        vector_docs: List[Document],
        bm25_docs: List[Document],
        k: int = 60,
    ) -> List[Document]:
        """使用 Reciprocal Rank Fusion 合并两路有序结果。"""
        scores: Dict[str, float] = {}
        doc_map: Dict[str, Document] = {}
        normalized_query = self._normalize_text(query)

        for rank, doc in enumerate(vector_docs, start=1):
            doc_id = self._doc_id(doc)
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
            doc_map[doc_id] = doc

        for rank, doc in enumerate(bm25_docs, start=1):
            doc_id = self._doc_id(doc)
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
            doc_map[doc_id] = doc

        for doc_id, doc in doc_map.items():
            # 在通用相关性分数之外，再加一道“菜名更像目标”的业务加分。
            scores[doc_id] = scores.get(doc_id, 0.0) + self._title_match_bonus(normalized_query, doc)

        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        results: List[Document] = []
        for doc_id, score in ranked:
            doc = doc_map[doc_id]
            doc.metadata["rrf_score"] = score
            results.append(doc)
        return results

    def _doc_id(self, doc: Document) -> str:
        chunk_id = doc.metadata.get("chunk_id")
        if chunk_id:
            return str(chunk_id)
        return str(hash(doc.page_content))

    def _title_match_bonus(self, normalized_query: str, doc: Document) -> float:
        normalized_title = self._normalize_text(doc.metadata.get("dish_name", ""))
        if not normalized_query or not normalized_title:
            return 0.0
        # 精确匹配权重最高，其次是包含关系匹配。
        if normalized_query == normalized_title:
            return 1.0
        if normalized_title in normalized_query:
            return 0.6
        if normalized_query in normalized_title:
            return 0.3
        return 0.0

    def _normalize_text(self, text: str) -> str:
        return re.sub(r"[\W_]+", "", text).lower()
