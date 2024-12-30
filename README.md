# data-pipeline
Code for the main ETL pipeline to be utilized to collect, scrape and transform training data.

## Installation
1. Clone the repository
2. Install the required packages using the following command:
```bash
make sync-requirements
```

## Configuration
The configuration file is located in the `config` folder and is named `config.json`. The configuration file contains the parameters
to be used in the ETL pipeline. Each main key of the JSON file represents the configuration of a different scraper.
The name of the key is the name of the scraper and the value is a dictionary containing the Pydantic model of the scraper configuration. For more examples, please take a look to the already implemented scrapers and their configurations.

## Usage

### Testing
For the usage with testing purposes, please create a `.env` file in the root of the project with the following content:
```bash
AWS_URL="http://localhost:9100"
AWS_REGION="us-east-1"
AWS_ACCESS_KEY="minio"
AWS_SECRET_KEY="minio1234"
AWS_BUCKET_NAME="esa-eve"

MINIO_URL="http://minio:9100"
```

Then, you can run the following command to execute the ETL pipeline:
```bash
make up
make run
```

The command `make up` will start the docker container and `make run` will execute the ETL pipeline.
It is possible to specify the name(s) of the scraper(s) to be executed by adding the `--scrapers` parameter to the `make run` command. E.g.:
```bash
make run --scrapers IOPScraper
```
or
```bash
make run args="--scrapers IOPScraper SpringerScraper"
```

The docker container are locally required, since a MinIO server is used to store the data and emulate a remote S3 bucket.
Every time the ETL pipeline is executed, the data is stored in the MinIO server and the configuration file is updated with the `done` key set to `True`.

**Note**: The `make up` command must be executed only once, since the docker container is started and the MinIO server is started.
The `make run` command can be executed multiple times to run the ETL pipeline.
The `make down` command can be executed to stop the docker container.

### Production
For the usage with productive purposes, please create a `.env` file in the root of the project with the following content:
```bash
AWS_URL=<the_url_of_your_s3_bucket>
AWS_REGION=<aws_region>
AWS_ACCESS_KEY=<aws_access_key>
AWS_SECRET_KEY=<aws_secret_key>
AWS_BUCKET_NAME=<aws_bucket_name>
```

Then, you can run the ETL pipeline as described in the previous section.

## HowTo: add a new Scraper
In order to add a new scraper, the following steps are required:
1. Create a new file in the `scraper` folder with the name of the scraper. E.g.: `new_editor_scraper.py`
2. If you need to add custom Pydantic model(s), please create a Python file in the `model` folder. E.g.: `new_editor_models.py`
3. Implement a new Pydantic model, representing the configuration of the new scraper, in the Python file previously
created (point 2.) by extending the `BaseConfigScraper` class. If you need enumerators, please extend `Enum` from the `base_enum` module.
4. Implement a new class in the file created at the 1st step. The class must inherit from the `BaseScraper` class and
implement the due methods / properties:
   - `config_model_type`: a `@property` returning the Pydantic model of the configuration of the scraper
   - `cookie_selector`: a `@property` returning the CSS selector of the cookie banner to be clicked, if any, or an empty string if the website does not have a cookie banner
   - `file_extension`: a `@property` returning the expected extension of the files to be downloaded / uploaded to the storage
   - `scrape`: a method that scrapes the website and returns the data
   - `post_process`: a method that post-processes the data scraped and returns a list of strings representing the URLs of the files to be downloaded / uploaded to the storage
5. Enrich the `config/config.json` file with the JSON-formatted configuration of the new scraper. Please, pay attention
that the key of the JSON object must be the name of the scraper and the value must be the Pydantic model of the configuration. Specifically, the JSON object must contain the following
keys:
   - `bucket_key`: the key of the bucket where the data will be stored
   - `base_url`: the key returning the base URL of the website to be scraped (optional)
   - `cookie_selector`: the key containing the CSS selector of the cookie banner to be clicked, if any, or an empty string if the website does not have a cookie banner (optional)
   - `file_extension`: the key returning the expected extension of the files to be downloaded / uploaded to the storage (optional, default ".pdf")