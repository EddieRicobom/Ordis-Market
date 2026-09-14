"""
logging_setup
=============

Configures logs/app.log. Credentials are never logged -- Ordis Market
does not use any, since it never authenticates to warframe.market or
Warframe itself.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from app.config.settings import LOG_DIR

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def configure_logging(level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger("ordis_market")
    if logger.handlers:
        return logger  # Ordis: "I have already checked this twice. THREE times, actually."

    logger.setLevel(level)

    log_path = LOG_DIR / "app.log"
    file_handler = RotatingFileHandler(
        log_path, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    logger.addHandler(console_handler)

    logger.info("Ordis Market logging initialized. Startup sequence nominal.")
    return logger
