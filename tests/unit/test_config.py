from config import DEFAULT_CONFIG, RAGConfig
from observability import LoggingSettings


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


def test_rag_config_reads_logging_settings_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("LOG_FILENAME", "service.log")
    monkeypatch.setenv("LOG_ENABLE_CONSOLE", "true")
    monkeypatch.setenv("LOG_ENABLE_FILE", "true")
    monkeypatch.setenv("LOG_MAX_BYTES", "2048")
    monkeypatch.setenv("LOG_BACKUP_COUNT", "3")

    config = RAGConfig.from_env()

    assert isinstance(config.logging, LoggingSettings)
    assert config.logging.level == "DEBUG"
    assert config.logging.log_filename == "service.log"
    assert config.logging.max_bytes == 2048
    assert config.logging.backup_count == 3
