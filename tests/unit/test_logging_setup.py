import logging

from logging_setup import LoggingSettings, configure_logging


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
    logger = logging.getLogger("tests.logging_setup")
    logger.info("hello log file")

    assert log_path.exists()
    assert "hello log file" in log_path.read_text(encoding="utf-8")
