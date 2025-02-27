#!/usr/bin/env python3
"""
Script that reads a JSON file with groups of files for SHA256 and copies the first file of each group
to a new location with a UUID name while keeping the original extension.
"""

import os
import json
import uuid
import argparse
import logging
import boto3
from dotenv import load_dotenv
from botocore.exceptions import ClientError
from concurrent.futures import ThreadPoolExecutor

# logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_arguments():
    parser = argparse.ArgumentParser(description="Copy unique files with UUID names.")
    parser.add_argument("--input", required=True, help="SHA256 Groups JSON File")
    parser.add_argument("--bucket", required=True, help="S3 Bucket name")
    parser.add_argument(
        "--dest-prefix",
        default="raw_data_new/egup/",
        help="Destination directory prefix (default: raw_data_new/egup/)"
    )
    parser.add_argument("--workers", type=int, default=10, help="Number of concurrent workers (default: 10)")
    parser.add_argument("--dry-run", action="store_true", help="Run without making changes")
    return parser.parse_args()


def get_file_extension(file_path):
    """Extracts the file extension from the path."""
    return os.path.splitext(file_path)[1]


def copy_file_with_uuid(args):
    """Copy a file with a new UUID name."""
    s3_client, bucket, source_key, dest_prefix, dry_run = args

    try:
        new_uuid = str(uuid.uuid4())
        file_extension = get_file_extension(source_key)
        dest_key = f"{dest_prefix}{new_uuid}{file_extension}"

        if dry_run:
            logger.info(f"[DRY RUN] I should copy {source_key} -> {dest_key}")
            return source_key, dest_key, True

        s3_client.copy_object(
            Bucket=bucket,
            CopySource={"Bucket": bucket, "Key": source_key},
            Key=dest_key
        )

        logger.info(f"Copiato {source_key} -> {dest_key}")
        return source_key, dest_key, True
    except ClientError as e:
        logger.error(f"Errore nella copia di {source_key}: {e}")
        return source_key, None, False


def main():
    load_dotenv()

    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_region = os.getenv("AWS_REGION", "us-east-1")
    aws_endpoint_url = os.getenv("AWS_ENDPOINT_URL", None)

    args = parse_arguments()

    if not args.dest_prefix.endswith("/"):
        args.dest_prefix += "/"

    s3_client = boto3.client(
        "s3",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=aws_region,
        endpoint_url=aws_endpoint_url
    )

    # load JSON file with SHA256 groups
    try:
        with open(args.input, "r") as f:
            sha256_groups = json.load(f)

        logger.info(f"File {args.input} with {len(sha256_groups)} SHA256 groups loaded")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error while loading the JSON file {args.input}: {e}")
        return

    # list of files to copy (first file for each SHA256 group)
    files_to_copy = []
    for sha256, files in sha256_groups.items():
        if not files:
            continue
        files_to_copy.append(files[0])  # get the first file only

    logger.info(f"Found {len(files_to_copy)} unique files to copy")

    if args.dry_run:
        logger.info("DRY RUN mode activated - no changes will be made")

    worker_args = [
        (s3_client, args.bucket, file_key, args.dest_prefix, args.dry_run)
        for file_key in files_to_copy
    ]

    # dictionary to track the results
    result_mapping = {}
    successful_copies = 0

    # parallel computing with ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        results = executor.map(copy_file_with_uuid, worker_args)

        for source_key, dest_key, success in results:
            result_mapping[source_key] = dest_key
            if success:
                successful_copies += 1

    # store the results in a JSON file
    output_file = f"copy_results_{uuid.uuid4()}.json"
    with open(output_file, "w") as f:
        json.dump(result_mapping, f, indent=2)

    # print some statistics
    logger.info(f"Process completed: {successful_copies}/{len(files_to_copy)} files successfully copied")
    logger.info(f"Map of results stored to {output_file}")


if __name__ == "__main__":
    main()

# example usage:
# $ python3 s3_copy_with_uuid.py --input sha256_groups.json --bucket my-bucket
