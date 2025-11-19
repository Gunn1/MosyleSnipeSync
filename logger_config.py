"""
Logging configuration for MosyleSnipeSync.
Sets up structured logging with file and console handlers.
"""
import logging
import logging.handlers
import os
from pathlib import Path


def setup_logging(log_dir="logs", log_level="INFO"):
    """
    Configure logging with file rotation and console output.

    Args:
        log_dir: Directory to store log files (created if doesn't exist)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Create logs directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    # Create logger
    logger = logging.getLogger("mosyle_snipe_sync")
    logger.setLevel(getattr(logging, log_level))

    # Remove any existing handlers to avoid duplicates
    logger.handlers.clear()

    # File handler with rotation (10MB, keep 10 files)
    file_handler = logging.handlers.RotatingFileHandler(
        log_path / "mosyle_snipe_sync.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10
    )
    file_handler.setLevel(getattr(logging, log_level))

    # Console handler for stderr
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level))

    # Formatter with timestamp (using {}-style to safely handle % characters in messages)
    formatter = logging.Formatter(
        "[{asctime}] {levelname:<8} {message}",
        datefmt="%Y-%m-%d %H:%M:%S",
        style="{"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def get_logger():
    """Get the configured logger instance."""
    return logging.getLogger("mosyle_snipe_sync")
