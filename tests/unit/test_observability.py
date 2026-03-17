import logging

from observability import LoggingSettings, MetricsRegistry, configure_logging


def test_configure_logging_creates_file_handler(tmp_path):
    settings = LoggingSettings(
        level="INFO",
        log_dir=str(tmp_path / "logs"),
        log_filename="service.log",
        enable_console=True,
        enable_file=True,
        max_bytes=1024,
        backup_count=2,
    )

    log_path = configure_logging(settings)
    logger = logging.getLogger("tests.observability")
    logger.info("hello log file")

    assert log_path.exists()
    assert "hello log file" in log_path.read_text(encoding="utf-8")


def test_metrics_registry_snapshot_tracks_requests():
    metrics = MetricsRegistry()

    metrics.record_request("GET", "/health", 200, 12.5)
    metrics.record_request("POST", "/chat", 200, 45.0)
    metrics.record_request("POST", "/chat/stream", 500, 90.0)

    snapshot = metrics.snapshot(
        system_ready=True,
        session_count=2,
        retrieval_cache_size=4,
        knowledge_base={"total_documents": 10},
    )

    assert snapshot["service_ready"] is True
    assert snapshot["requests_total"] == 3
    assert snapshot["errors_total"] == 1
    assert snapshot["chat_requests_total"] == 2
    assert snapshot["stream_requests_total"] == 1
    assert snapshot["sessions_total"] == 2
    assert snapshot["retrieval_cache_size"] == 4
    assert snapshot["knowledge_base"]["total_documents"] == 10
    assert snapshot["average_latency_ms"]["/chat"] == 45.0
