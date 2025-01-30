import hashlib
import os
from uuid import uuid4
import requests
from pydantic import BaseModel

from helper.logger import setup_logger
from helper.singleton import singleton
from service.database_manager import DatabaseManager


class Resource(BaseModel):
    id: int | None = None
    publisher: str
    bucket_key: str
    name: str
    sha256: str | None = None
    content: bytes | None = None


@singleton
class ResourceManager:
    def __init__(self):
        self._logger = setup_logger(self.__class__.__name__)
        self._database_manager = DatabaseManager()
        self._db_table_name = "resources"

    def get_by_url(
        self, publisher: str, root_key: str, source_url: str, file_extension: str, referer_url: str | None = None
    ) -> Resource:
        """
        Retrieve a resource from the database by its URL

        Args:
            publisher (str): The publisher of the resource
            root_key (str): The root key of the resource
            source_url (str): The URL of the resource
            file_extension (str): The file extension of the resource
            referer_url (str): The URL of the referer

        Returns:
            Resource | None: The resource if found, or None otherwise
        """
        from helper.utils import get_user_agent, get_interacting_proxy_config

        self._logger.info(f"Retrieving file from {source_url}")

        bucket_key = os.path.join(root_key, f"{uuid4()}.{file_extension}")  # Construct S3 key
        result = Resource(publisher=publisher, bucket_key=bucket_key, name=source_url)
        try:
            # Download content from the URL
            proxy = get_interacting_proxy_config()
            response = requests.get(
                source_url,
                headers={
                    "User-Agent": get_user_agent(),
                    "Accept": "application/pdf,*/*",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Referer": referer_url,
                },
                proxies={
                    "http": proxy,
                    "https": proxy,
                },
                verify=False,  # Equivalent to -k flag in curl (ignore SSL certificate warnings)
            )
            response.raise_for_status()  # Check for request errors

            # calculate the sha256 of the content
            result.content = response.content
            result.sha256 = hashlib.sha256(response.content).hexdigest()

            # search for the resource in the database by using the sha256
            records = self._database_manager.search_records(
                self._db_table_name, {"sha256": result.sha256, "publisher": publisher}, limit=1
            )
            if records:
                result = Resource(**records[0])
        except Exception as e:
            self._logger.error(f"Failed to retrieve the resource {source_url}. Error: {e}")
        finally:
            return result

    def get_by_content(self, publisher: str, root_key: str, source_path: str) -> Resource:
        """
        Retrieve a resource from the database by its content

        Args:
            publisher (str): The publisher of the resource
            root_key (str): The root key of the resource
            source_path (str): The name of the resource

        Returns:
            Resource | None: The resource if found, or None otherwise
        """
        file_extension = os.path.basename(source_path).split(".")[-1]
        bucket_key = os.path.join(root_key, f"{uuid4()}.{file_extension}")  # Construct S3 key

        result = Resource(bucket_key=bucket_key, name=source_path, publisher=publisher)
        try:
            with open(os.path.join(source_path), "rb") as f:
                result.content = f.read()
                result.sha256 = hashlib.sha256().hexdigest()

            records = self._database_manager.search_records(
                self._db_table_name, {"sha256": result.sha256, "publisher": publisher}, limit=1
            )
            if records:
                return Resource(**records[0])
        except Exception as e:
            self._logger.error(f"Failed to retrieve the resource {source_path}. Error: {e}")
        finally:
            return result

    def store(self, resource: Resource) -> int:
        """
        Store the resource in the database

        Args:
            resource (Resource): The resource to store

        Returns:
            ID of the appended record
        """
        resource_dict = resource.model_dump()
        if "content" in resource_dict:
            del resource_dict["content"]
        if "id" in resource_dict:
            del resource_dict["id"]
        return self._database_manager.insert_record(self._db_table_name, resource_dict)

    @property
    def table_name(self) -> str:
        return self._db_table_name
