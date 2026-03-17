from langchain_core.documents import Document

from rag.retriever import HybridRetriever


def test_title_bonus_promotes_exact_dish_match_to_top1():
    retriever = HybridRetriever.__new__(HybridRetriever)
    exact_doc = Document(
        page_content="皮蛋瘦肉粥做法",
        metadata={"dish_name": "皮蛋瘦肉粥", "chunk_id": "exact"},
    )
    similar_doc = Document(
        page_content="黄瓜皮蛋汤做法",
        metadata={"dish_name": "黄瓜皮蛋汤", "chunk_id": "similar"},
    )

    reranked = retriever._rrf_rerank(
        "皮蛋瘦肉粥怎么做",
        vector_docs=[similar_doc, exact_doc],
        bm25_docs=[similar_doc, exact_doc],
    )

    assert reranked[0].metadata["dish_name"] == "皮蛋瘦肉粥"
