#!/usr/bin/env python3
"""
Script that recursively explores an S3 directory and groups files based on their SHA256 hash.
S3 connection parameters are loaded from a .env file
"""

import os
import hashlib
import boto3
from botocore.exceptions import ClientError
from collections import defaultdict
import argparse
import json
from concurrent.futures import ThreadPoolExecutor
import logging
from dotenv import load_dotenv

# logging
logging.basicConfig(level=logging.INFO,format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_arguments():
    parser = argparse.ArgumentParser(description="Group file S3 per hash SHA256.")
    parser.add_argument("--bucket", required=True, help="S3 Bucket name")
    parser.add_argument("--prefix", required=True, help="Prefix of the folder to inspect (e.g. raw_data/egup/)")
    parser.add_argument(
        "--output",
        default="sha256_groups.json",
        help="Output files for the results (default: sha256_groups.json)"
    )
    parser.add_argument("--workers", type=int, default=10, help="Number of concurrent workers (default: 10)")
    parser.add_argument("--skip-empty", action="store_true", help="Skip empty files")
    return parser.parse_args()


def get_sha256_from_s3(s3_client, bucket, key):
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        sha256_hash = hashlib.sha256()

        # Reads file in blocks to handle large files
        for chunk in iter(lambda: response["Body"].read(4096), b""):
            sha256_hash.update(chunk)

        return sha256_hash.hexdigest()
    except ClientError as e:
        logger.error(f"Error in calculating SHA256 for {key}: {e}")
        return None


def list_all_files(s3_client, bucket, prefix):
    """Recursively lists all files in an S3 bucket with the specified prefix."""
    files = []
    paginator = s3_client.get_paginator("list_objects_v2")

    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        if "Contents" in page:
            for obj in page["Contents"]:
                files.append(obj["Key"])

    return files


def process_file(args):
    """Function to process a single file (used with ThreadPoolExecutor)."""
    s3_client, bucket, file_key, skip_empty = args

    try:
        # is the file empty?
        response = s3_client.head_object(Bucket=bucket, Key=file_key)
        file_size = response["ContentLength"]

        if skip_empty and file_size == 0:
            logger.info(f"File empty skipped: {file_key}")
            return None, file_key

        sha256 = get_sha256_from_s3(s3_client, bucket, file_key)
        logger.info(f"SHA256 for {file_key}: {sha256}")
        return sha256, file_key
    except ClientError as e:
        logger.error(f"Error while processing {file_key}: {e}")
        return None, file_key


def main():
    load_dotenv()

    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_region = os.getenv("AWS_REGION", "us-east-1")
    aws_endpoint_url = os.getenv("AWS_ENDPOINT_URL", None)

    args = parse_arguments()

    if not args.prefix.endswith("/"):
        args.prefix += "/"

    s3_client = boto3.client(
        "s3",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=aws_region,
        endpoint_url=aws_endpoint_url
    )

    logger.info(f"Exploring the bucket {args.bucket} with the prefix {args.prefix}")

    all_files = list_all_files(s3_client, args.bucket, args.prefix)
    logger.info(f"Found {len(all_files)} to process")

    # dictionary to group files per hash SHA256
    file_groups = defaultdict(list)

    # parallel computing with ThreadPoolExecutor
    worker_args = [(s3_client, args.bucket, file_key, args.skip_empty) for file_key in all_files]
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        results = executor.map(process_file, worker_args)

        for sha256, file_key in results:
            if not sha256:
                continue
            file_groups[sha256].append(file_key)

    # get only the groups with more than one file
    # duplicate_groups = {sha: files for sha, files in file_groups.items() if len(files) > 1}

    # order the groups by SHA256
    sorted_groups = {sha: file_groups[sha] for sha in sorted(file_groups.keys())}

    # store the results in a JSON file
    with open(args.output, "w") as f:
        json.dump(sorted_groups, f, indent=2)

    # print some statistics
    total_unique_hashes = len(sorted_groups)
    files_with_duplicates = sum(1 for files in file_groups.values() if len(files) > 1)
    total_duplicates = sum(len(files) - 1 for files in file_groups.values() if len(files) > 1)

    logger.info(f"Completed. Found {total_unique_hashes} unique hashes.")
    logger.info(f"Files with duplicates: {files_with_duplicates}")
    logger.info(f"Total number of duplicates: {total_duplicates}")
    logger.info(f"Results stored into: {args.output}")


if __name__ == "__main__":
    main()

# example usage:
# $ python3 s3_sha256_grouper.py --bucket my-bucket --prefix raw_data/egup/ --output sha256_groups.json --workers 10 --skip-empty
