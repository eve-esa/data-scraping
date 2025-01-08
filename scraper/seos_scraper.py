import os
from typing import List, Type, Dict
from bs4 import Tag

from helper.utils import get_unique, get_scraped_url
from model.seos_models import SeosConfig, SeosSource
from scraper.base_scraper import BaseScraper


class SeosScraper(BaseScraper):
    @property
    def config_model_type(self) -> Type[SeosConfig]:
        """
        Return the configuration model type.

        Returns:
            Type[SeosConfig]: The configuration model type
        """
        return SeosConfig

    def scrape(self, model: SeosConfig) -> Dict[str, List[str]] | None:
        """
        Scrape the Seos sources for HTML links.

        Args:
            model (SeosConfig): The configuration model.

        Returns:
            Dict[str, List[str]]: a dictionary collecting, for each source, the corresponding list of the HTML links. If no link was found, return None.
        """
        links = {}
        for source in model.sources:
            links[source.url] = self.__scrape_source(source)

        return links if links else None

    def __scrape_source(self, source: SeosSource) -> List[str]:
        """
        Scrape the source URL for HTML links.

        Args:
            source (SeosSource): The source to scrape.

        Returns:
            List[str]: A list of HTML links.
        """
        self._logger.info(f"Processing Source {source.url}")
        scraper = self._scrape_url(source.url)

        html_tags = []
        for i in range(1, source.chapters + 1):
            try:
                i_str = f"{i}" if i >= 10 else f"0{i}"  # Add leading zero if needed

                html_tags.extend(
                    scraper.find_all("a", href=lambda href: href and i_str in href and source.search in href)
                )
            except Exception as e:
                self._logger.error(f"Failed to process Chapter {i}. Error: {e}")

        html_links = get_unique([get_scraped_url(tag, os.path.join(self.base_url, source.folder)) for tag in html_tags])
        self._logger.info(f"HTML links found: {len(html_links)}")

        return html_links

    def post_process(self, scrape_output: Dict[str, List[str]]) -> List[str]:
        """
        Extract the href attribute from the links.

        Args:
            scrape_output (Dict[str, List[Tag]]): A dictionary collecting, for each source, the corresponding list of Tag objects containing the tags to the HTML links.

        Returns:
            List[str]: A list of strings containing the HTML links
        """

        links = [link for links in scrape_output.values() for link in links]
        return get_unique(links)
