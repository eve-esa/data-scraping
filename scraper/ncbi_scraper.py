from bs4 import ResultSet

from scraper.base_pagination_publisher_scraper import BasePaginationPublisherScraper


class NCBIScraper(BasePaginationPublisherScraper):
    @property
    def base_url(self) -> str:
        return "https://www.ncbi.nlm.nih.gov"

    @property
    def cookie_selector(self) -> str:
        return ""

    def _scrape_page(self, url: str, page_number: int, source_number: int, show_logs: bool = True) -> ResultSet | None:
        """
        Scrape the PubMed page of the collection from pagination for PDF links.

        Args:
            url (str): The URL to scrape.
            page_number (int): The page number.
            source_number (int): The source number.
            show_logs (bool): Whether to show logs.

        Returns:
            ResultSet: A ResultSet (i.e., a list) or a list of Tag objects containing the tags to the PDF links, or None if something went wrong.
        """
        try:
            scraper = self._scrape_url(url)

            # Find all PDF links using appropriate class or tag (if lambda returns True, it will be included in the list)
            pdf_tag_list = scraper.find_all("a", href=lambda href: href and "/articles/" in href and ".pdf" in href, class_="view")

            if show_logs:
                self._logger.info(f"PDF links found: {len(pdf_tag_list)}")
            return pdf_tag_list
        except Exception as e:
            self._logger.error(f"Failed to process URL {url}. Error: {e}")
            return None