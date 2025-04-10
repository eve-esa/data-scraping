import mysql.connector
import boto3
import os



def get_files():
    # === MySQL connection ===

    db_host = os.getenv("DB_HOST")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_name = os.getenv("DB_NAME")

    # Establish MySQL connection
    db = mysql.connector.connect(
        host=db_host,
        user=db_user,
        password=db_password,
        database=db_name
    )


    cursor = db.cursor()
    query = """
    SELECT bucket_key 
    FROM uploaded_resources 
    INNER JOIN uploaded_resources_metadata 
    ON uploaded_resources_metadata.uploaded_resource_id = uploaded_resources.id 
    WHERE uploaded_resources.scraper = "AMSScraper"  
    AND JSON_UNQUOTE(JSON_EXTRACT(uploaded_resources_metadata.metadata, '$."cc-by-license"')) = 'true'
    """
    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()
    db.close()
    return results


def load_on_s3():
    # === S3 setup ===
    s3 = boto3.client('s3')
    source_bucket = 'llm4eo-s3'
    destination_bucket = 'llm4eo-s3'  # can be the same as source
    destination_prefix = 'raw_data_new/amc_cc_license'  # e.g., 'cc-by-licensed/'

    results = get_files()

    for (bucket_key,) in results:
        # Define new key in destination folder
        filename = os.path.basename(bucket_key)
        new_key = os.path.join(destination_prefix, filename)

        # Copy object
        copy_source = {
            'Bucket': source_bucket,
            'Key': bucket_key
        }
        print('Copying {} to {}'.format(bucket_key, new_key))

        s3.copy_object(
            CopySource=copy_source,
            Bucket=destination_bucket,
            Key=new_key
        )
        print(f"Copied {bucket_key} to {new_key}")


if __name__ == "__main__":
    load_on_s3()