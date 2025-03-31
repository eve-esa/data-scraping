from typing import Type

from model.sql_models import UploadedResourceMetadata
from repository.base_repository import BaseRepository


class UploadedResourceMetadataRepository(BaseRepository):
    @property
    def model_type(self) -> Type[UploadedResourceMetadata]:
        return UploadedResourceMetadata
