from typing import List, TypeAlias, Dict

from model.base_mapped_models import BaseMappedBaseConfig, BaseMappedBaseSource


class NASANTRSConfig(BaseMappedBaseConfig):
    base_url: str
    sources: List[BaseMappedBaseSource]


NASANTRSScraperOutput: TypeAlias = Dict[str, List[str]]
