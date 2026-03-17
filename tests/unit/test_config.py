from config import DEFAULT_CONFIG, RAGConfig


def test_default_runtime_flags_match_current_latency_strategy():
    assert DEFAULT_CONFIG.enable_thinking is False
    assert DEFAULT_CONFIG.history_window == 4


def test_rag_config_can_be_loaded_from_api_embedding_env(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "api")
    monkeypatch.setenv("EMBEDDING_DEVICE", "cpu")
    monkeypatch.setenv("EMBEDDING_LOCAL_FILES_ONLY", "false")

    config = RAGConfig.from_env()

    assert config.embedding_provider == "api"
    assert config.use_api_embeddings is True
    assert config.embedding_device == "cpu"
    assert config.embedding_local_files_only is False
