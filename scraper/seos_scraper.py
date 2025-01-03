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

    def scrape(self, model: SeosConfig) -> Dict[str, List[Tag]] | None:
        """
        Scrape the Seos sources for HTML links.

        Args:
            model (SeosConfig): The configuration model.

        Returns:
            Dict[str, List[Tag]]: a dictionary collecting, for each source, the corresponding list of Tag objects containing the tags to the HTML links. If no tag was found, return None.
        """

        links = {}
        for source in model.sources:
            links[source.url] = self.__scrape_source(source)

        return links if links else None

    def __scrape_source(self, source: SeosSource) -> List[Tag]:
        """
        Scrape the source URL for HTML links.

        Args:
            source (SeosSource): The source to scrape.

        Returns:
            List[Tag]: A list of Tag objects containing the HTML links.
        """
        self._logger.info(f"Processing Source {source.url}")

        html_tags = []
        for i in range(1, source.chapters + 1):
            self._logger.info(f"Processing Chapter {i}")
            try:
                i_str = f"-c{i}" if i >= 10 else f"-c0{i}"
                scraper = self._scrape_url(source.url.format(**{"chapter": i_str[2:]}))

                html_tags.extend(scraper.find_all("a", href=lambda href: href and i_str in href))
            except Exception as e:
                self._logger.error(f"Failed to process Chapter {i}. Error: {e}")

        self._logger.info(f"HTML links found: {len(html_tags)}")
        return html_tags

    def post_process(self, scrape_output: Dict[str, List[Tag]]) -> List[str]:
        """
        Extract the href attribute from the links.

        Args:
            scrape_output (Dict[str, List[Tag]]): A dictionary collecting, for each source, the corresponding list of Tag objects containing the tags to the HTML links.

        Returns:
            List[str]: A list of strings containing the HTML links
        """

        links = [get_scraped_url(tag, self.base_url) for tags in scrape_output.values() for tag in tags]
        return get_unique(links)
