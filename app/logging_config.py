import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging() -> None:
    log_directory = Path("logs")
    log_directory.mkdir(exist_ok=True)

    handler = RotatingFileHandler(
        log_directory / "app.log",
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )

    logger = logging.getLogger("operations_assistant")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.propagate = False
