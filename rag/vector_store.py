import logging
import os
from importlib import import_module
from pathlib import Path
from typing import Dict, List, Optional

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from .dashscope_embeddings import DashScopeEmbeddings


logger = logging.getLogger(__name__)


class VectorStore:
    """向量索引层：负责向量化、建索引和索引加载。"""

    DEFAULT_CACHE_FOLDER = os.getenv("HF_HOME", str(Path.home() / ".cache" / "huggingface"))

    def __init__(
        self,
        model_name: str,
        index_save_path: str,
        embedding_provider: str = "local",
        embedding_device: str = "cpu",
        embedding_local_files_only: bool = False,
    ):
        self.model_name = model_name
        self.index_save_path = Path(index_save_path)
        self.embedding_provider = embedding_provider
        self.embedding_device = embedding_device
        self.embedding_local_files_only = embedding_local_files_only
        self.embeddings = None
        self.vectorstore: Optional[FAISS] = None

    def build_and_save_index(self, chunks: List[Document]) -> FAISS:
        """根据切块构建 FAISS 索引，并保存到本地。"""
        embeddings = self._ensure_embeddings()
        self.vectorstore = FAISS.from_documents(chunks, embeddings)
        self.index_save_path.mkdir(parents=True, exist_ok=True)
        self.vectorstore.save_local(str(self.index_save_path))
        logger.info("Built and saved FAISS index to %s", self.index_save_path)
        return self.vectorstore

    def load_index(self) -> Optional[FAISS]:
        """尝试从本地加载已有索引。"""
        if not self.index_save_path.exists():
            logger.info("Index path does not exist: %s", self.index_save_path)
            return None

        try:
            embeddings = self._ensure_embeddings()
            self.vectorstore = FAISS.load_local(
                str(self.index_save_path),
                embeddings,
                allow_dangerous_deserialization=True,
            )
            logger.info("Loaded FAISS index from %s", self.index_save_path)
            return self.vectorstore
        except Exception:
            logger.exception("Failed to load FAISS index from %s", self.index_save_path)
            return None

    def is_compatible_with_parent_docs(
        self,
        parent_docs: Dict[str, Document],
        expected_chunk_count: int,
    ) -> bool:
        """
        检查现有索引是否仍然和当前文档集兼容。

        当前会校验三类问题：
        - chunk 数量是否一致
        - 索引中的父文档集合是否和当前文档集合一致
        - 同一 parent_id 对应的内容哈希是否一致
        """
        if self.vectorstore is None:
            return False

        stored_docs = list(getattr(self.vectorstore.docstore, "_dict", {}).values())
        if len(stored_docs) != expected_chunk_count:
            logger.info(
                "Vector index chunk count mismatch: index=%s current=%s",
                len(stored_docs),
                expected_chunk_count,
            )
            return False

        current_parent_ids = set(parent_docs.keys())
        stored_parent_ids = {
            str(doc.metadata.get("parent_id"))
            for doc in stored_docs
            if doc.metadata.get("parent_id")
        }
        if stored_parent_ids != current_parent_ids:
            logger.info(
                "Vector index parent set mismatch: index=%s current=%s",
                sorted(stored_parent_ids),
                sorted(current_parent_ids),
            )
            return False

        for doc in stored_docs:
            parent_id = doc.metadata.get("parent_id")
            if not parent_id:
                continue
            current_parent = parent_docs.get(parent_id)
            if current_parent is None:
                logger.info(
                    "Vector index parent_id mismatch detected for source=%s parent_id=%s",
                    doc.metadata.get("source"),
                    parent_id,
                )
                return False

            stored_hash = doc.metadata.get("content_hash")
            current_hash = current_parent.metadata.get("content_hash")
            if stored_hash != current_hash:
                logger.info(
                    "Vector index content hash mismatch detected for parent_id=%s stored=%s current=%s",
                    parent_id,
                    stored_hash,
                    current_hash,
                )
                return False

        return True

    def _ensure_embeddings(self):
        if self.embeddings is not None:
            return self.embeddings

        if self.embedding_provider == "api":
            logger.info("Initializing API embeddings")
            self.embeddings = DashScopeEmbeddings()
            return self.embeddings

        if self.embedding_provider != "local":
            raise ValueError(
                f"Unsupported embedding provider: {self.embedding_provider}. "
                "Expected 'api' or 'local'."
            )

        model_kwargs = {"device": self.embedding_device}
        if self.embedding_local_files_only:
            model_kwargs["local_files_only"] = True

        # 离线模式下优先解析到本地 snapshot 路径，避免继续按 repo 名远程查找。
        model_source = self._resolve_model_source()

        logger.info(
            "Initializing local embeddings with model=%s device=%s local_only=%s",
            model_source,
            self.embedding_device,
            self.embedding_local_files_only,
        )
        self.embeddings = self._load_huggingface_embeddings()(
            model_name=model_source,
            cache_folder=self.DEFAULT_CACHE_FOLDER,
            model_kwargs=model_kwargs,
            encode_kwargs={"normalize_embeddings": True},
            show_progress=True,
        )
        logger.info("Embedding backend ready")
        return self.embeddings

    def _resolve_model_source(self) -> str:
        if not self.embedding_local_files_only:
            return self.model_name

        snapshot_dir = self._find_cached_snapshot_dir()
        if snapshot_dir is not None:
            return str(snapshot_dir)
        return self.model_name

    def _find_cached_snapshot_dir(self) -> Optional[Path]:
        repo_dir = Path(self.DEFAULT_CACHE_FOLDER) / "hub" / f"models--{self.model_name.replace('/', '--')}"
        refs_main = repo_dir / "refs" / "main"
        snapshots_dir = repo_dir / "snapshots"

        if refs_main.exists():
            revision = refs_main.read_text(encoding="utf-8").strip()
            candidate = snapshots_dir / revision
            if candidate.exists():
                return candidate

        if snapshots_dir.exists():
            snapshots = sorted(item for item in snapshots_dir.iterdir() if item.is_dir())
            if snapshots:
                return snapshots[-1]

        return None

    def _load_huggingface_embeddings(self):
        try:
            module = import_module("langchain_huggingface")
            return module.HuggingFaceEmbeddings
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "Local embeddings require `langchain-huggingface` and "
                "`sentence-transformers`. Install `requirements-local.txt` "
                "or build the image with INSTALL_LOCAL_EMBEDDINGS=true."
            ) from exc
