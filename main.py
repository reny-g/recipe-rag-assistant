import logging
import time
from collections import OrderedDict
from pathlib import Path
from typing import Dict, Generator, Iterable, List, Optional, Union

from config import DEFAULT_CONFIG, RAGConfig, load_project_env
from observability import configure_logging
from rag import DataPreparation, HybridRetriever, RagGenerator, VectorStore


load_project_env()
configure_logging(DEFAULT_CONFIG.logging)
logger = logging.getLogger(__name__)


class RagSystem:
    """RAG system orchestration layer."""

    RETRIEVAL_CACHE_SIZE = 128

    def __init__(self, config: Optional[RAGConfig] = None):
        self.config = config or DEFAULT_CONFIG
        self._validate_paths()

        print("[1/4] Loading data module...")
        self.data_module = DataPreparation(self.config.data_path)

        print("[2/4] Initializing embeddings...")
        self.index_module = VectorStore(
            model_name=self.config.embedding_model,
            index_save_path=self.config.index_save_path,
            embedding_provider=self.config.embedding_provider,
            embedding_device=self.config.embedding_device,
            embedding_local_files_only=self.config.embedding_local_files_only,
        )
        self.retrieval_module: Optional[HybridRetriever] = None

        print("[3/4] Initializing generator...")
        self.generation_module = RagGenerator(
            model_name=self.config.llm_model,
            enable_thinking=self.config.enable_thinking,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            contextualize_timeout=self.config.contextualize_timeout,
            answer_timeout=self.config.answer_timeout,
            contextualize_max_retries=self.config.contextualize_max_retries,
            answer_max_retries=self.config.answer_max_retries,
        )
        self.session_store: Dict[str, List[Dict[str, str]]] = {}
        self._retrieval_cache: OrderedDict[
            tuple[str, tuple[tuple[str, str], ...], int],
            List,
        ] = OrderedDict()
        print("[4/4] Ready.")

    def build_knowledge_base(self) -> None:
        logger.info("Starting knowledge base build")
        print("\nBuilding knowledge base")
        print("  - Loading documents...")
        self.data_module.load_documents()
        print("  - Splitting documents...")
        chunks = self.data_module.split_into_chunks()
        print(f"  - Generated {len(chunks)} chunks")

        print("  - Loading or building vector index...")
        vector_store = self.index_module.load_index()
        if vector_store is None:
            logger.info("No existing index found. Building a new FAISS index.")
            print("  - No local index found. Building a new one...")
            vector_store = self.index_module.build_and_save_index(chunks)
        elif not self.index_module.is_compatible_with_parent_docs(
            self.data_module.parent_docs,
            expected_chunk_count=len(chunks),
        ):
            logger.info("Existing vector index is incompatible with current documents. Rebuilding.")
            print("  - Existing index metadata is incompatible. Rebuilding...")
            vector_store = self.index_module.build_and_save_index(chunks)
        else:
            logger.info("Existing vector index loaded.")
            print("  - Loaded existing vector index")

        self.retrieval_module = HybridRetriever(vector_store, chunks, default_k=self.config.top_k)
        self._log_knowledge_base_stats()
        print("  - Knowledge base ready\n")

    def get_runtime_status(self) -> dict:
        knowledge_base = self.data_module.get_statistics() if self.retrieval_module is not None else {}
        return {
            "sessions_total": len(self.session_store),
            "retrieval_cache_size": len(self._retrieval_cache),
            "knowledge_base": knowledge_base,
        }

    def answer_query(
        self,
        query: str,
        session_id: str = "default",
        stream: bool = False,
    ) -> Union[str, Generator[str, None, None]]:
        self._ensure_ready_for_query()
        request_started_at = time.perf_counter()

        history = self._get_recent_history(session_id)
        if not history and self.generation_module.is_context_dependent_query(query):
            answer = (
                "这个问题依赖上一轮上下文，但当前会话里没有可参考的菜品。"
                "请先说明具体菜名，例如“陈皮排骨汤要炖多久？”"
            )
            self._append_message(session_id, "user", query)
            self._append_message(session_id, "assistant", answer)
            self._log_reply_latency(query, request_started_at, event="missing_context")
            return answer

        contextualized_query = self.generation_module.contextualize_query(query, history)
        filters = self._extract_filters_from_query(contextualized_query)

        relevant_chunks = self._retrieve_chunks(contextualized_query, filters)
        if not relevant_chunks:
            answer = "抱歉，知识库中没有找到相关菜谱信息。请尝试其他菜名或更具体的关键词。"
            self._append_message(session_id, "user", query)
            self._append_message(session_id, "assistant", answer)
            self._log_reply_latency(query, request_started_at, event="no_results")
            return answer

        relevant_docs = self.data_module.get_parent_documents(relevant_chunks)
        self._log_retrieval_summary(query, contextualized_query, relevant_chunks, relevant_docs)

        if stream:
            return self._stream_and_store(
                session_id,
                query,
                request_started_at,
                self.generation_module.generate_answer(
                    query,
                    relevant_docs,
                    history,
                    stream=True,
                ),
            )

        answer = self.generation_module.generate_answer(query, relevant_docs, history, stream=False)
        if not isinstance(answer, str):
            answer = "".join(answer)
        self._append_message(session_id, "user", query)
        self._append_message(session_id, "assistant", answer)
        self._log_reply_latency(query, request_started_at, event="non_stream_complete")
        return answer

    def run_interactive(self) -> None:
        session_id = "default"
        stream_enabled = True
        while True:
            query = input(
                "请输入您的问题（输入 exit 退出，/clear 清空记忆，/stream on|off 切换流式输出）："
            ).strip()
            if not query:
                continue
            if query.lower() == "exit":
                break
            if query == "/clear":
                self.clear_session(session_id)
                print("当前会话记忆已清空。")
                continue
            if query.lower() in {"/stream", "/stream on"}:
                stream_enabled = True
                print("已开启流式输出。")
                continue
            if query.lower() == "/stream off":
                stream_enabled = False
                print("已关闭流式输出。")
                continue

            result = self.answer_query(query, session_id=session_id, stream=stream_enabled)
            if isinstance(result, str):
                print(result)
            else:
                for piece in result:
                    print(piece, end="", flush=True)
                print()

    def clear_session(self, session_id: str = "default") -> None:
        self.session_store.pop(session_id, None)

    def _validate_paths(self) -> None:
        data_path = Path(self.config.data_path)
        if not data_path.exists():
            raise FileNotFoundError(f"Data path does not exist: {data_path}")

    def _ensure_ready_for_query(self) -> None:
        if self.retrieval_module is None:
            raise ValueError("Please build the knowledge base before querying.")

    def _get_recent_history(self, session_id: str) -> List[Dict[str, str]]:
        history = self.session_store.get(session_id, [])
        return history[-self.config.history_window :]

    def _append_message(self, session_id: str, role: str, content: str) -> None:
        self.session_store.setdefault(session_id, []).append({"role": role, "content": content})
        self.session_store[session_id] = self.session_store[session_id][-self.config.history_window :]

    def _stream_and_store(
        self,
        session_id: str,
        query: str,
        request_started_at: float,
        stream: Generator[str, None, None],
    ) -> Generator[str, None, None]:
        self._append_message(session_id, "user", query)

        def _wrapped():
            chunks: List[str] = []
            first_chunk_logged = False
            for piece in stream:
                if piece and not first_chunk_logged:
                    self._log_reply_latency(query, request_started_at, event="first_stream_chunk")
                    first_chunk_logged = True
                chunks.append(piece)
                yield piece
            if not first_chunk_logged:
                self._log_reply_latency(query, request_started_at, event="stream_completed_without_chunk")
            self._append_message(session_id, "assistant", "".join(chunks))

        return _wrapped()

    def _retrieve_chunks(self, query: str, filters: dict[str, str]):
        assert self.retrieval_module is not None
        cache_key = self._retrieval_cache_key(query, filters)
        cached_chunks = self._cache_get(self._retrieval_cache, cache_key)
        if cached_chunks is not None:
            logger.info("Retrieval cache hit for query=%r filters=%s", query, filters)
            return list(cached_chunks)

        if filters:
            chunks = self.retrieval_module.metadata_filtered_search(
                query,
                filters,
                top_k=self.config.top_k,
            )
        else:
            chunks = self.retrieval_module.hybrid_search(query, top_k=self.config.top_k)

        self._cache_set(self._retrieval_cache, cache_key, list(chunks), self.RETRIEVAL_CACHE_SIZE)
        return chunks

    def _retrieval_cache_key(
        self,
        query: str,
        filters: dict[str, str],
    ) -> tuple[str, tuple[tuple[str, str], ...], int]:
        return (query.strip(), tuple(sorted(filters.items())), self.config.top_k)

    def _extract_filters_from_query(self, query: str) -> dict[str, str]:
        filters: dict[str, str] = {}

        for category in DataPreparation.get_supported_categories():
            if category in query:
                filters["category"] = category
                break

        for difficulty in sorted(DataPreparation.get_supported_difficulties(), key=len, reverse=True):
            if difficulty in query:
                filters["difficulty"] = difficulty
                break

        return filters

    def _cache_get(self, cache: OrderedDict, key):
        value = cache.get(key)
        if value is None:
            return None
        cache.move_to_end(key)
        return value

    def _cache_set(self, cache: OrderedDict, key, value, max_size: int) -> None:
        cache[key] = value
        cache.move_to_end(key)
        while len(cache) > max_size:
            cache.popitem(last=False)

    def _log_knowledge_base_stats(self) -> None:
        stats = self.data_module.get_statistics()
        logger.info(
            "Knowledge base ready: docs=%s chunks=%s categories=%s difficulties=%s",
            stats.get("total_documents", 0),
            stats.get("total_chunks", 0),
            list(stats.get("categories", {}).keys()),
            stats.get("difficulties", {}),
        )

    def _log_retrieval_summary(
        self,
        original_query: str,
        contextualized_query: str,
        chunks: Iterable,
        docs: Iterable,
    ) -> None:
        chunk_labels = []
        for chunk in chunks:
            dish_name = chunk.metadata.get("dish_name", "未知菜品")
            preview = chunk.page_content.splitlines()[0].strip() if chunk.page_content else "内容片段"
            chunk_labels.append(f"{dish_name}({preview[:30]})")

        doc_names = [doc.metadata.get("dish_name", "未知菜品") for doc in docs]
        logger.info("User query: %s", original_query)
        if contextualized_query != original_query:
            logger.info("Contextualized query: %s", contextualized_query)
        logger.info("Retrieved chunks: %s", ", ".join(chunk_labels) if chunk_labels else "none")
        logger.info("Retrieved documents: %s", ", ".join(doc_names) if doc_names else "none")

    def _log_reply_latency(self, query: str, started_at: float, event: str) -> None:
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        logger.info("Reply latency: event=%s elapsed_ms=%.1f query=%r", event, elapsed_ms, query)


if __name__ == "__main__":
    system = RagSystem()
    system.build_knowledge_base()
    system.run_interactive()
