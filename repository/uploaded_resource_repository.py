import hashlib
import os
from typing import List, Type
from uuid import uuid4

from model.sql_models import UploadedResource
from repository.base_repository import BaseRepository


class UploadedResourceRepository(BaseRepository):
    def get_by_url(
        self, scraper: str, root_key: str, source_url: str, file_extension: str, referer_url: str | None = None
    ) -> UploadedResource:
        """
        Retrieve a resource from the database by its URL

        Args:
            scraper (str): The scraper of the resource
            root_key (str): The root key of the resource
            source_url (str): The URL of the resource
            file_extension (str): The file extension of the resource
            referer_url (str): The URL of the referer

        Returns:
            UploadedResource | None: The resource if found, or None otherwise
        """
        from helper.utils import get_resource_from_remote

        self._logger.info(f"Retrieving file from {source_url}")

        bucket_key = os.path.join(root_key, f"{uuid4()}.{file_extension}")  # Construct S3 key
        result = UploadedResource(scraper=scraper, bucket_key=bucket_key, source=source_url)
        try:
            content = get_resource_from_remote(source_url, referer_url)

            # calculate the sha256 of the content
            result.content = content
            result.sha256 = hashlib.sha256(content).hexdigest()

            # search for the resource in the database by using the sha256
            record = self.get_one_by({"sha256": result.sha256, "scraper": scraper})
            if record:
                result = record
        except Exception as e:
            self._logger.error(f"Failed to retrieve the resource {source_url}. Error: {e}")
        finally:
            return result

    def get_by_content(self, scraper: str, root_key: str, source_path: str) -> UploadedResource:
        """
        Retrieve a resource from the database by its content

        Args:
            scraper (str): The scraper of the resource
            root_key (str): The root key of the resource
            source_path (str): The name of the resource

        Returns:
            UploadedResource | None: The resource if found, or None otherwise
        """
        file_extension = os.path.basename(source_path).split(".")[-1]
        bucket_key = os.path.join(root_key, f"{uuid4()}.{file_extension}")  # Construct S3 key

        result = UploadedResource(bucket_key=bucket_key, source=source_path, scraper=scraper)
        try:
            with open(os.path.join(source_path), "rb") as f:
                result.content = f.read()
                result.sha256 = hashlib.sha256().hexdigest()

            record = self.get_one_by({"sha256": result.sha256, "scraper": scraper})
            if record:
                return record
        except Exception as e:
            self._logger.error(f"Failed to retrieve the resource {source_path}. Error: {e}")
        finally:
            return result

    @property
    def table_name(self) -> str:
        return "uploaded_resources"

    @property
    def model_type(self) -> Type[UploadedResource]:
        return UploadedResource

    @property
    def model_fields_excluded(self) -> List[str]:
        return ["id", "content"]
