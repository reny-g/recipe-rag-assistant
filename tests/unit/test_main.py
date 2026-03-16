from collections import OrderedDict

from main import RagSystem
from config import RAGConfig


class FakeRetriever:
    def __init__(self):
        self.hybrid_calls = 0
        self.filtered_calls = 0

    def hybrid_search(self, query: str, top_k: int = 5):
        # 用计数器代替真实检索，方便判断缓存有没有生效。
        self.hybrid_calls += 1
        return [f"{query}:{top_k}"]

    def metadata_filtered_search(self, query: str, filters: dict, top_k: int = 5):
        self.filtered_calls += 1
        return [f"{query}:{filters}:{top_k}"]


def build_system_for_unit_tests() -> RagSystem:
    # 绕过完整初始化，只保留当前单元测试真正需要的字段。
    system = RagSystem.__new__(RagSystem)
    system.config = RAGConfig(data_path=".", index_save_path=".")
    system.session_store = {}
    system._retrieval_cache = OrderedDict()
    system.retrieval_module = FakeRetriever()
    return system


def test_retrieval_cache_avoids_duplicate_hybrid_search_calls():
    system = build_system_for_unit_tests()

    first = system._retrieve_chunks("黄瓜皮蛋汤怎么做", {})
    second = system._retrieve_chunks("黄瓜皮蛋汤怎么做", {})

    assert first == second
    assert system.retrieval_module.hybrid_calls == 1


def test_append_message_respects_history_window():
    system = build_system_for_unit_tests()

    for index in range(6):
        system._append_message("demo", "user", f"msg-{index}")

    stored = system.session_store["demo"]
    assert len(stored) == system.config.history_window
    assert [item["content"] for item in stored] == ["msg-2", "msg-3", "msg-4", "msg-5"]
