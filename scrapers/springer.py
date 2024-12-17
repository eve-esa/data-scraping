from typing import Type, List

from scrapers.base import BaseConfigScraper
from scrapers.iop import IOPJournal, IOPConfig, IOPScraper


class SpringerJournal(IOPJournal):
    issue_url: str  # url contains volume and issue number. Eg: https://www.mdpi.com/2072-4292/1/3


class SpringerConfig(IOPConfig):
    journals: List[SpringerJournal]


class SpringerScraper(IOPScraper):
    @property
    def model_class(self) -> Type[BaseConfigScraper]:
        return SpringerConfig
