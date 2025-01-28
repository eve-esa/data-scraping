import logging
import sys
from multiprocessing import Queue
from logging.handlers import QueueHandler
import colorlog


def setup_logger(name: str, log_file: str = "scraping.log") -> logging.Logger:
    """
    Configure the main process logger with both file and colored console output.

    Args:
        name: Logger name
        log_file: Optional path to log file
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        logger.handlers.clear()

    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    console_handler = colorlog.StreamHandler(sys.stdout)
    color_formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s [%(processName)s] [%(name)s] %(levelname)s: %(message)s%(reset)s",
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

    # File handler
    file_formatter = logging.Formatter(
        "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler = logging.FileHandler(log_file, mode="w")
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    return logger


def setup_worker_logging(queue: Queue, name: str):
    """
    Configure logging for worker processes to send logs to queue.

    Args:
        queue (Queue): Multiprocessing queue for logs
        name (str): Logger name to maintain consistency with main process
    """
    logger = logging.getLogger(name)

    # Clear any existing handlers
    if logger.handlers:
        logger.handlers.clear()

    # Set up the queue handler
    queue_handler = QueueHandler(queue)
    logger.addHandler(queue_handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
