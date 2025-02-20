import hashlib
import os
from typing import Type
from uuid import uuid4

from model.base_models import BaseConfig
from model.sql_models import UploadedResource
from repository.base_repository import BaseRepository


class UploadedResourceRepository(BaseRepository):
    def get_by_url(self, scraper: str, source_url: str, config: BaseConfig) -> UploadedResource:
        """
        Retrieve a resource from the database by its URL

        Args:
            scraper (str): The scraper of the resource
            source_url (str): The URL of the resource
            config (BaseConfig): The configuration of the resource

        Returns:
            UploadedResource | None: The resource if found, or None otherwise
        """
        from helper.utils import get_resource_from_remote_by_request, get_resource_from_remote_by_scraping

        bucket_key = config.bucket_key
        file_extension = config.file_extension
        loading_tag = config.loading_tag
        cookie_selector = config.cookie_selector
        request_with_proxy = config.request_with_proxy

        self._logger.info(f"Retrieving file from {source_url}")

        result = UploadedResource(
            scraper=scraper, bucket_key=os.path.join(bucket_key, f"{uuid4()}.{file_extension}"), source=source_url
        )
        try:
            content = get_resource_from_remote_by_request(
                source_url, request_with_proxy
            ) if file_extension == "pdf" else get_resource_from_remote_by_scraping(
                source_url, loading_tag, cookie_selector
            )

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
    def model_type(self) -> Type[UploadedResource]:
        return UploadedResource
