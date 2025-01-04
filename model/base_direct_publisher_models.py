from typing import List

from model.base_models import BaseConfig


class BaseDirectPublisherConfig(BaseConfig):
    urls: List[str]
