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

        file_extension = config.file_extension

        main_folder = os.getenv("AWS_MAIN_FOLDER", "raw_data")
        root_key = config.bucket_key.format(main_folder=main_folder)
        bucket_key = os.path.join(root_key, f"{uuid4()}.{file_extension}")  # Construct S3 key

        loading_tag = config.loading_tag
        cookie_selector = config.cookie_selector
        request_with_proxy = config.request_with_proxy

        self._logger.info(f"Retrieving file from {source_url}")

        result = UploadedResource(scraper=scraper, bucket_key=bucket_key, source=source_url)
        message = None
        try:
            content = get_resource_from_remote_by_request(
                source_url, request_with_proxy
            ) if file_extension == "pdf" else get_resource_from_remote_by_scraping(
                source_url, loading_tag, cookie_selector
            )
        except Exception as e:
            self._logger.error(f"Failed to retrieve the content from {source_url}. Error: {e}")
            content = None
            message = str(e)

        return self.__update_resource(result, scraper, content=content, message=message)

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

        main_folder = os.getenv("AWS_MAIN_FOLDER", "raw_data")
        root_key = root_key.format(main_folder=main_folder)
        bucket_key = os.path.join(root_key, f"{uuid4()}.{file_extension}")  # Construct S3 key

        result = UploadedResource(bucket_key=bucket_key, source=source_path, scraper=scraper)
        message = None
        try:
            with open(source_path, "rb") as f:
                content = f.read()
        except Exception as e:
            self._logger.error(f"Failed to retrieve the content from {source_path}. Error: {e}")
            content = None
            message = str(e)

        return self.__update_resource(result, scraper, content=content, message=message)

    def __update_resource(
        self, resource: UploadedResource, scraper: str, content: bytes | None = None, message: str | None = None
    ) -> UploadedResource:
        if not content:
            resource.content_retrieved = False
            resource.message = message
            return resource

        # calculate the sha256 of the content
        sha256 = hashlib.sha256(content).hexdigest()

        # search for the resource in the database by using the sha256
        record = self.get_one_by({"sha256": sha256, "scraper": scraper})
        if record:
            resource = record

        resource.content = content
        resource.sha256 = sha256
        resource.content_retrieved = True

        return resource

    @property
    def model_type(self) -> Type[UploadedResource]:
        return UploadedResource
