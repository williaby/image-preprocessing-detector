"""Logging configuration for benchmarks framework.

Provides consistent logging setup across all benchmark runners and tasks.

"""

import logging
import sys
from pathlib import Path


def setup_benchmark_logging(
    log_level: str = "INFO",
    log_file: Path | None = None,
) -> logging.Logger:
    """Setup logging configuration for benchmarks.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional file path to write logs to

    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger("benchmarks")
    logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    logger.handlers = []

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)  # Always capture DEBUG to file
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_benchmark_logger(name: str | None = None) -> logging.Logger:
    """Get a logger for a specific benchmark module.

    Args:
        name: Logger name (will be prefixed with 'benchmarks.')

    Returns:
        Logger instance
    """
    if name:
        return logging.getLogger(f"benchmarks.{name}")
    return logging.getLogger("benchmarks")
