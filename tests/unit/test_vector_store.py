import pytest
from langchain_core.documents import Document

from rag.vector_store import VectorStore


class FakeDocStore:
    def __init__(self, docs):
        self._dict = {str(index): doc for index, doc in enumerate(docs)}


class FakeVectorStore:
    def __init__(self, docs):
        self.docstore = FakeDocStore(docs)


def make_chunk(parent_id: str, content_hash: str) -> Document:
    return Document(
        page_content="chunk",
        metadata={
            "parent_id": parent_id,
            "content_hash": content_hash,
            "chunk_id": f"{parent_id}-chunk-0",
        },
    )


def make_parent(parent_id: str, content_hash: str) -> Document:
    return Document(
        page_content="parent",
        metadata={
            "parent_id": parent_id,
            "content_hash": content_hash,
        },
    )


def build_vector_store_with_docs(docs) -> VectorStore:
    store = VectorStore.__new__(VectorStore)
    store.vectorstore = FakeVectorStore(docs)
    return store


def test_index_is_compatible_when_parent_set_and_hashes_match():
    stored_docs = [make_chunk("parent-a", "hash-a"), make_chunk("parent-b", "hash-b")]
    parent_docs = {
        "parent-a": make_parent("parent-a", "hash-a"),
        "parent-b": make_parent("parent-b", "hash-b"),
    }
    store = build_vector_store_with_docs(stored_docs)

    assert store.is_compatible_with_parent_docs(parent_docs, expected_chunk_count=2) is True


def test_index_is_incompatible_when_document_content_changes():
    stored_docs = [make_chunk("parent-a", "old-hash")]
    parent_docs = {
        "parent-a": make_parent("parent-a", "new-hash"),
    }
    store = build_vector_store_with_docs(stored_docs)

    assert store.is_compatible_with_parent_docs(parent_docs, expected_chunk_count=1) is False


def test_index_is_incompatible_when_document_is_added():
    stored_docs = [make_chunk("parent-a", "hash-a")]
    parent_docs = {
        "parent-a": make_parent("parent-a", "hash-a"),
        "parent-b": make_parent("parent-b", "hash-b"),
    }
    store = build_vector_store_with_docs(stored_docs)

    assert store.is_compatible_with_parent_docs(parent_docs, expected_chunk_count=1) is False


def test_index_is_incompatible_when_document_is_removed():
    stored_docs = [make_chunk("parent-a", "hash-a"), make_chunk("parent-b", "hash-b")]
    parent_docs = {
        "parent-a": make_parent("parent-a", "hash-a"),
    }
    store = build_vector_store_with_docs(stored_docs)

    assert store.is_compatible_with_parent_docs(parent_docs, expected_chunk_count=2) is False


def test_invalid_embedding_provider_is_rejected():
    store = VectorStore(model_name="demo", index_save_path=".", embedding_provider="invalid")

    with pytest.raises(ValueError):
        store._ensure_embeddings()
