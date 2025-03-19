from typing import Type, List
from bs4 import Tag
from urllib.parse import urlparse, parse_qs

from helper.utils import get_scraped_url_by_bs_tag
from model.base_pagination_publisher_models import BasePaginationPublisherConfig, BasePaginationPublisherScrapeOutput
from scraper.base_pagination_publisher_scraper import BasePaginationPublisherScraper


class IntechOpenScraper(BasePaginationPublisherScraper):
    def __init__(self):
        super().__init__()
        self.__page_size = None
        self.__forbidden_keywords = ("accounts.google.com", "site:", "translate.google.com")

    @property
    def config_model_type(self) -> Type[BasePaginationPublisherConfig]:
        return BasePaginationPublisherConfig

    def scrape(self) -> BasePaginationPublisherScrapeOutput | None:
        pdf_tags = []
        for idx, source in enumerate(self._config_model.sources):
            self.__page_size = source.page_size
            pdf_tags.extend(self._scrape_landing_page(source.landing_page_url, idx + 1))

        return {"IntechOpen": [
            get_scraped_url_by_bs_tag(tag, self._config_model.base_url) for tag in pdf_tags
        ]} if pdf_tags else None

    def _scrape_landing_page(self, landing_page_url: str, source_number: int) -> List[Tag]:
        return self._scrape_pagination(landing_page_url, source_number, base_zero=True, page_size=self.__page_size)

    def _scrape_page(self, url: str) -> List[Tag] | None:
        def get_pdf_tags(paper_tag: Tag) -> List[Tag]:
            intech_open_url = get_scraped_url_by_bs_tag(paper_tag, self._config_model.base_url)
            if ".pdf" in intech_open_url:
                return [Tag(name="a", attrs={"href": intech_open_url})]
            try:
                # visit the Google link
                scraper_ = self._scrape_url(intech_open_url)
            except:
                return []
            # get the iframe source, which is the real PDF link to download, if it exists
            if iframe := scraper_.find(
                "iframe", src=True, class_=lambda class_: class_ and "pdf-object" in class_
            ):
                pdf_url = iframe.get("src")
                # from pdf_url, get the `file` parameter of the query string
                return [Tag(name="a", attrs={"href": parse_qs(urlparse(pdf_url).query)["file"][0]})]
            # check whether the visited page contains `a` tags with `class` attribute containing "chapter__title"
            chapter_tags = scraper_.find_all(
                "a", class_=lambda class_: class_ and "chapter__title" in class_
            )
            result = []
            for chapter_tag in chapter_tags:
                result.extend(get_pdf_tags(Tag(name="a", attrs={"href": chapter_tag.get("href")})))
            return result if len(result) > 0 else [Tag(name="a", attrs={"href": intech_open_url})]

        try:
            # first of all, scrape the Google Search URL
            scraper = self._scrape_url(url)

            paper_tags = scraper.find_all(
                "a",
                href=lambda href: href and self._config_model.base_url in href and not any(
                    x in href for x in self.__forbidden_keywords
                ),
            )

            pdf_tag_list = []
            tags_with_profiles = []
            for paper_tag in paper_tags:
                if "profiles" in paper_tag.get("href"):
                    tags_with_profiles.append(paper_tag)
                else:
                    pdf_tag_list.extend(get_pdf_tags(paper_tag))

            self._logger.debug(f"PDF links found: {len(pdf_tag_list)}")
            if not pdf_tag_list and not tags_with_profiles:
                self._save_failure(url)
                return None

            return pdf_tag_list
        except Exception as e:
            self._log_and_save_failure(url, f"Failed to process URL {url}. Error: {e}")
            return None

    def _is_valid_tag_list(self, page_tag_list: List | None) -> bool:
        return page_tag_list is not None
