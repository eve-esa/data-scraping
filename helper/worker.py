import logging
from multiprocessing import Queue, Process
from logging.handlers import QueueHandler, QueueListener
from typing import Dict, Type
import time
from pydantic import ValidationError
import queue

from scraper.base_scraper import BaseScraper


def setup_worker_logging(queue_: Queue, name: str):
    """
    Configure logging for worker processes to send logs to queue.

    Args:
        queue_ (Queue): Multiprocessing queue for logs
        name (str): Logger name to maintain consistency with main process
    """
    logger = logging.getLogger(name)

    # Clear any existing handlers
    if logger.handlers:
        logger.handlers.clear()

    # Set up the queue handler
    queue_handler = QueueHandler(queue_)
    logger.addHandler(queue_handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False


def setup_workers(
    discovered_scrapers: Dict[str, Type[BaseScraper]],
    config: Dict[str, Dict],
    target_function: callable,
    logger_name: str,
    log_file: str = "logs/scraping.log",
):
    from helper.utils import setup_logger

    # Create logging queue
    log_queue = Queue()

    # Setup main process logger
    logger = setup_logger(logger_name, log_file)

    # Create and start listener
    listener = QueueListener(log_queue, *logger.handlers, respect_handler_level=True)
    listener.start()

    try:
        processes = []
        for name_scraper, class_type_scraper in discovered_scrapers.items():
            config_scraper = config.get(name_scraper)
            if config_scraper is None:
                logger.error(f"Scraper {name_scraper} not found in configured scrapers")
                continue

            try:
                process = Process(
                    target=target_function,
                    args=(log_queue, class_type_scraper, config_scraper),
                    name=name_scraper
                )
                process.start()
                time.sleep(0.5)
                processes.append(process)
            except ValidationError as e:
                logger.error(f"Error resuming scraper {name_scraper}: {e}")

        # Wait for all processes to complete
        for process in processes:
            process.join()
    finally:
        # Ensure the queue is empty before stopping
        while not log_queue.empty():
            try:
                record = log_queue.get_nowait()
                logger.handle(record)
            except queue.Empty:
                break

        listener.stop()
        # Small delay to ensure all logs are processed
        time.sleep(0.1)
