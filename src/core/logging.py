"""Logging utilities"""

import logging
from typing import Optional


def setup_logging(verbose: bool = False, name: Optional[str] = None) -> logging.Logger:
    """
    Setup and return configured logger

    Args:
        verbose: Enable DEBUG level if True, else INFO
        name: Logger name (default: root logger)

    Returns:
        Configured logger instance
    """
    level = logging.DEBUG if verbose else logging.INFO

    if name:
        logger = logging.getLogger(name)
    else:
        logger = logging.getLogger()

    logger.setLevel(level)

    # Avoid duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(level)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get logger by name"""
    return logging.getLogger(name)
