import logging
import os
import sys
from logging.handlers import RotatingFileHandler
import colorlog

# Dictionary to store loggers
_loggers = {}


def setup_logger(name: str, log_file: str = "logs/scraping.log") -> logging.Logger:
    """
    Configure the main process logger with both file and colored console output.

    Args:
        name: Logger name
        log_file: Optional path to log file
    """
    # Return existing logger if already configured
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    # Only set up handlers if they don't exist
    if not logger.handlers:
        # Console handler with colors
        console_handler = colorlog.StreamHandler(sys.stdout)
        color_formatter = colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s [%(name)s] %(levelname)s: %(message)s%(reset)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            log_colors={
                "DEBUG": "blue",
                "INFO": "white",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red,bg_white",
            }
        )
        console_handler.setFormatter(color_formatter)
        logger.addHandler(console_handler)

        # Rotating file handler
        file_formatter = logging.Formatter(
            "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        file_handler = RotatingFileHandler(
            filename=log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    # Store logger for reuse
    _loggers[name] = logger
    return logger
