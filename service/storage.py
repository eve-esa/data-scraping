import os
from typing import Final
import boto3

from helper.logger import setup_logger
from helper.singleton import singleton
from model.sql_models import UploadedResource


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
        self.logger: Final = setup_logger(__name__)

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
                self.logger.debug(f"Bucket {self.bucket_name} already exists in S3.")
                return

        # Create bucket, if it does not exist
        region = os.getenv("AWS_REGION")
        if region is None:
            self.client.create_bucket(Bucket=self.bucket_name)
        else:
            location = {"LocationConstraint": region}
            self.client.create_bucket(Bucket=self.bucket_name, CreateBucketConfiguration=location)

    def upload_content(self, resource: UploadedResource) -> bool:
        self.logger.info(f"Uploading Source: {resource.source} to {resource.bucket_key}")
        try:
            # Upload to S3
            self.client.put_object(Bucket=self.bucket_name, Key=resource.bucket_key, Body=resource.content)
            self.logger.info(f"Successfully uploaded to S3: {resource.bucket_key}")

            return True
        except Exception as e:
            self.logger.error(f"Failed to upload content from {resource.source} to {resource.bucket_key}. Error: {e}")
            return False
