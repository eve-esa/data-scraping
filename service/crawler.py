import os
from typing import Any
from urllib.parse import urlparse
import scrapy
from urllib.parse import urljoin
from scrapy.http import Response

from helper.utils import get_user_agent, get_random_proxy


class CustomUserAgentMiddleware:
    """
    Middleware to random set an User Agent per request
    """
    def process_request(self, request, spider):
        request.headers["User-Agent"] = get_user_agent()


class CustomProxyMiddleware:
    """
    Middleware to set a dynamic proxy
    """
    def process_request(self, request, spider):
        request.meta["proxy"] = get_random_proxy()


class EveSpider(scrapy.Spider):
    name = "eve_spider"
    custom_settings = {
        "DOWNLOAD_DELAY": 1.0,
        "ROBOTSTXT_OBEY": True,
        "CONCURRENT_REQUESTS": 8,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 4,
        "DOWNLOADER_MIDDLEWARES": {
            "service.crawler.CustomUserAgentMiddleware": 400,
            "service.crawler.CustomProxyMiddleware": 410,
            "scrapy.downloadermiddlewares.cookies.CookiesMiddleware": 700,
        },
    }

    def __init__(self, name: str | None = None, **kwargs: Any):
        super().__init__(name, **kwargs)

        self.start_urls = kwargs.get("start_urls")
        if not self.start_urls:
            raise ValueError("start_urls is required")

        self._download_folder_path = kwargs.get("download_folder_path")
        if not self._download_folder_path:
            raise ValueError("download_folder_path is required")
        os.makedirs(self._download_folder_path, exist_ok=True)

    def parse(self, response: Response, **kwargs: Any):
        """
        Parse the response and save the HTML content to a file.

        Args:
            response (Response): The response object.
            **kwargs (Any): Additional arguments.

        Returns:
            Generator: A generator of the next requests to make.
        """
        if not response.headers.get("Content-Type", b"").startswith(b"text/html"):
            self.logger.info(f"Skipping non-HTML content: {response.url}")
            return

        page_name = response.url.split("/")[-2] or "index"
        with open(os.path.join(self._download_folder_path, f"{page_name}.html"), "wb") as f:
            f.write(response.body)

        for href in response.css("a::attr(href)").getall():
            next_page = urljoin(response.url, href)
            if self.is_same_domain(response.url, next_page) and not self.is_resource_file(next_page):
                yield scrapy.Request(next_page, callback=self.parse)

    def is_same_domain(self, base_url: str, target_url: str) -> bool:
        """
        Check if the base URL and the target URL are from the same domain.

        Args:
            base_url (str): The base URL.
            target_url (str): The target URL.

        Returns:
            bool: True if the base URL and the target URL are from the same domain, False otherwise.
        """
        base_parts = urlparse(base_url)
        target_parts = urlparse(target_url)

        if base_parts.netloc != target_parts.netloc:
            return False

        if not base_parts.path or base_parts.path == '/':
            return base_parts.netloc == target_parts.netloc

        return target_parts.path.rstrip('/').startswith(base_parts.path.rstrip('/'))

    def is_resource_file(self, url: str) -> bool:
        """
        Check if the URL points to a resource file (images, documents, etc.)

        Args:
            url (str): The URL to check.

        Returns:
            bool: True if the URL points to a resource file, False otherwise.
        """
        resource_extensions = {
            '.jpg', '.jpeg', '.png', '.gif', '.pdf', '.doc', '.docx',
            '.xls', '.xlsx', '.zip', '.rar', '.mp3', '.mp4', '.avi',
            '.mov', '.wmv', '.flv', '.svg', '.webp'
        }
        return any(url.lower().endswith(ext) for ext in resource_extensions)
