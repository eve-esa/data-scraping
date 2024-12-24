import logging
import os
from typing import Final
import boto3
import requests
from botocore.exceptions import ClientError
from pydantic import BaseModel

from singleton import singleton


class PDFName(BaseModel):
    journal: str
    volume: str
    issue: str


@singleton
class S3Storage:
    def __init__(self):
        self.client = boto3.client(
            "s3",
            region_name=os.getenv("AWS_REGION"),
            endpoint_url=os.getenv("AWS_URL"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
            aws_secret_access_key=os.getenv("AWS_SECRET_KEY")
        )
        self.bucket_name: Final[str] = os.getenv("AWS_BUCKET_NAME")
        self.logger: Final = logging.getLogger(__name__)

    def __str__(self):
        return f"S3Storage: {self.bucket_name}"

    def __repr__(self):
        return self.__str__()

    def upload(self, root_key: str, source_url: str) -> bool:
        from utils import get_pdf_name

        s3_key = os.path.join(root_key, get_pdf_name(source_url))  # Construct S3 key

        self.logger.info(f"Uploading Source: {source_url} to {s3_key}")

        # Check if the file already exists in S3
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=s3_key)
            self.logger.warning(f"{s3_key} already exists in S3, skipping upload.")
            return True  # Exit the function if the file exists
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                # The object does not exist, proceed to upload
                pass
            else:
                # Handle other exceptions, e.g. permissions
                self.logger.error(f"Error checking if {s3_key} exists in S3: {e}")
                return False

        try:
            # Download PDF content from the URL
            response = requests.get(source_url)
            response.raise_for_status()  # Check for request errors

            # Upload to S3
            self.client.put_object(Bucket=self.bucket_name, Key=s3_key, Body=response.content)
            self.logger.info(f"Successfully uploaded to S3: {s3_key}")

            return True
        except Exception as e:
            self.logger.error(f"Failed to upload source {source_url} to {s3_key}. Error: {e}")

            return False
