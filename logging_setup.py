import logging
import os
import sys
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path


LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


@dataclass(frozen=True)
class LoggingSettings:
    level: str = "INFO"
    log_dir: str = "logs"
    log_filename: str = "app.log"
    enable_console: bool = True
    enable_file: bool = True
    max_bytes: int = 10 * 1024 * 1024
    backup_count: int = 5

    @property
    def log_path(self) -> Path:
        return Path(self.log_dir) / self.log_filename


def configure_logging(settings: LoggingSettings) -> Path:
    root_logger = logging.getLogger()
    configured_path = getattr(root_logger, "_recipe_log_path", None)
    target_path = str(settings.log_path.resolve())
    if configured_path == target_path:
        return Path(configured_path)

    level = getattr(logging, settings.level.upper(), logging.INFO)
    formatter = logging.Formatter(LOG_FORMAT)
    handlers: list[logging.Handler] = []

    if settings.enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        handlers.append(console_handler)

    if settings.enable_file:
        log_path = settings.log_path
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=settings.max_bytes,
            backupCount=settings.backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    root_logger.handlers.clear()
    root_logger.setLevel(level)
    for handler in handlers:
        root_logger.addHandler(handler)

    for logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastapi", "openai._base_client"):
        current = logging.getLogger(logger_name)
        current.handlers.clear()
        current.propagate = True
        if logger_name == "openai._base_client":
            current.setLevel(logging.WARNING)

    root_logger._recipe_log_path = target_path
    return Path(target_path)


def logging_settings_from_env(project_root: Path) -> LoggingSettings:
    log_dir = os.getenv("LOG_DIR", str(project_root / "logs"))
    return LoggingSettings(
        level=os.getenv("LOG_LEVEL", "INFO"),
        log_dir=log_dir,
        log_filename=os.getenv("LOG_FILENAME", "app.log"),
        enable_console=_env_bool("LOG_ENABLE_CONSOLE", True),
        enable_file=_env_bool("LOG_ENABLE_FILE", True),
        max_bytes=_env_int("LOG_MAX_BYTES", 10 * 1024 * 1024),
        backup_count=_env_int("LOG_BACKUP_COUNT", 5),
    )


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value is not None and value.strip() else default
