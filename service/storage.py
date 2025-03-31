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

    def move(self, source: str, destination: str) -> bool:
        """
        Move an object from one location to another in the same bucket.

        Args:
            source (str): The key of the object to move.
            destination (str): The key of the destination object.

        Returns:
            bool: True if the object was moved successfully, False otherwise.
        """
        try:
            self.client.copy_object(
                Bucket=self.bucket_name,
                CopySource={"Bucket": self.bucket_name, "Key": source},
                Key=destination
            )
            self.client.delete_object(Bucket=self.bucket_name, Key=source)
            self.logger.info(f"Moved {source} to {destination}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to move {source} to {destination}. Error: {e}")
            return False

    def move_folder(self, source_prefix: str, destination_prefix: str) -> bool:
        """
        Move all objects in a folder from one location to another in the same bucket.

        Args:
            source_prefix (str): The prefix of the objects to move.
            destination_prefix (str): The prefix of the destination objects.

        Returns:
            bool: True if the objects were moved successfully, False otherwise.
        """
        try:
            paginator = self.client.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=source_prefix)

            for page in pages:
                if "Contents" not in page:
                    continue

                for obj in page["Contents"]:
                    source_key = obj["Key"]
                    destination_key = source_key.replace(source_prefix, destination_prefix, 1)

                    self.move(source_key, destination_key)

            return True
        except Exception as e:
            self.logger.error(f"Failed to move folder {source_prefix} to {destination_prefix}. Error: {e}")
            return False

    def get(self, bucket_key: str) -> bytes:
        """
        Retrieve an object from S3.

        Args:
            bucket_key (str): The key of the object to retrieve.

        Returns:
            The content of the object as bytes.
        """
        response = self.client.get_object(Bucket=self.bucket_name, Key=bucket_key)
        return response["Body"].read()
