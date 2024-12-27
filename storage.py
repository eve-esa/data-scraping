import logging
import os
from typing import Final
import boto3
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
        self.client: boto3.session.Session.client = boto3.client(
            "s3",
            region_name=os.getenv("AWS_REGION"),
            endpoint_url=os.getenv("AWS_URL"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
            aws_secret_access_key=os.getenv("AWS_SECRET_KEY")
        )
        self.bucket_name: Final[str] = os.getenv("AWS_BUCKET_NAME")
        self.logger: Final = logging.getLogger(__name__)

        self.create_bucket_if_not_existing()

    def __str__(self):
        return f"S3Storage: {self.bucket_name}"

    def __repr__(self):
        return self.__str__()

    def create_bucket_if_not_existing(self):
        """
        Create an S3 bucket in a specified region. If a region is not specified, the bucket is created in the S3 default
        region (us-east-1).
        """
        # Check if the bucket already exists
        for bucket in self.client.list_buckets()["Buckets"]:
            if bucket["Name"] == self.bucket_name:
                self.logger.info(f"Bucket {self.bucket_name} already exists in S3.")
                return

        # Create bucket, if it does not exist
        region = os.getenv("AWS_REGION")
        if region is None:
            self.client.create_bucket(Bucket=self.bucket_name)
        else:
            location = {"LocationConstraint": region}
            self.client.create_bucket(Bucket=self.bucket_name, CreateBucketConfiguration=location)

    def upload(
        self,
        root_key: str,
        source_url: str,
        file_extension: str,
        referer_url: str | None = None,
        with_tor: bool = False,
    ) -> bool:
        from utils import get_pdf_name, get_content_response

        s3_key = os.path.join(root_key, get_pdf_name(source_url, file_extension))  # Construct S3 key

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
            content = get_content_response(source_url, referer_url=referer_url, with_tor=with_tor)

            # Upload to S3
            self.client.put_object(Bucket=self.bucket_name, Key=s3_key, Body=content)
            self.logger.info(f"Successfully uploaded to S3: {s3_key}")

            return True
        except Exception as e:
            self.logger.error(f"Failed to upload source {source_url} to {s3_key}. Error: {e}")

            return False
