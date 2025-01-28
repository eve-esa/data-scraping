import logging
import sys
import colorlog


def setup_logger(name: str, log_file: str = "scraping.log"):
    """
    Configure a logger with both file and colored console output.

    Args:
        name: Logger name (typically __name__ from the calling module)
        log_file: Path to log file
    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    file_handler = logging.FileHandler(log_file, mode="w")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

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

    logger.propagate = False

    return logger