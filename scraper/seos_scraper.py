from typing import List, Type, Dict
from bs4 import Tag
import os
from pydantic import BaseModel

from scraper.base_scraper import BaseConfigScraper, BaseScraper


class SeosSource(BaseModel):
    url: str
    chapters: int


class SeosConfig(BaseConfigScraper):
    sources: List[SeosSource]


class SeosScraper(BaseScraper):
    @property
    def cookie_selector(self) -> str:
        return ""

    @property
    def config_model_type(self) -> Type[SeosConfig]:
        """
        Return the configuration model type.

        Returns:
            Type[SeosConfig]: The configuration model type
        """
        return SeosConfig

    @property
    def base_url(self) -> str:
        return "https://seos-project.eu"

    @property
    def file_extension(self) -> str:
        """
        Return the file extension of the source files.

        Returns:
            str: The file extension of the source files
        """
        return ".html"

    def scrape(self, model: SeosConfig) -> Dict[str, List[Tag]] | None:
        """
        Scrape the Seos sources for HTML links.

        Args:
            model (SeosConfig): The configuration model.

        Returns:
            Dict[str, List[Tag]]: a dictionary collecting, for each source, the corresponding ResultSet (i.e., a list) or a list of Tag objects containing the tags to the HTML links. If no tag was found, return None.
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
                scraper = self._scrape_url_by_bs4(source.url.format(**{"chapter": i_str[2:]}))

                html_tags.extend(scraper.find_all("a", href=lambda href: href and i_str in href))
            except Exception as e:
                self._logger.error(f"Failed to process Chapter {i}. Error: {e}")

        self._logger.info(f"HTML links found: {len(html_tags)}")
        return html_tags

    def post_process(self, scrape_output: Dict[str, List[Tag]]) -> List[str]:
        """
        Extract the href attribute from the links.

        Args:
            scrape_output (Dict[str, List[Tag]]): A dictionary collecting, for each source, the corresponding ResultSet (i.e., a list) or a list of Tag objects containing the tags to the HTML links.

        Returns:
            List[str]: A list of strings containing the HTML links
        """

        links = []
        for key_url in scrape_output.keys():
            links.extend(
                [
                    key_url.replace(os.path.basename(key_url), tag.get("href"))
                    for tag in scrape_output[key_url]
                ]
            )
        return list(set(links))
