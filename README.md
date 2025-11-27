# Eve Data Scraping
Code for the main ETL pipeline to be utilized to collect and scrape data.

## Pre-requisites
For the local usage, please create a virtual environment in the `venv` folder by running the following command:
```bash
python3 -m venv venv
```

Then, activate the virtual environment by running the following command:
```bash
source venv/bin/activate
```

Now that the virtual environment is activated, please create a `.env` file in the root of the project with the following
content (ask the project maintainer for the values of the keys):
```bash
AWS_URL=http://minio:9100
AWS_REGION=us-east-1
AWS_ACCESS_KEY=minio
AWS_SECRET_KEY=minio1234
AWS_BUCKET_NAME=esa-eve
AWS_MAIN_FOLDER=raw_data

MINIO_URL=http://minio:9100

HEADLESS_BROWSER=<true|false>
XVFB_MODE=<true|false>

DB_HOST=mysql
DB_PORT=3306
DB_NAME=esa_eve
DB_USER=root
DB_PASSWORD=root

INTERACTING_PROXY_HOST=brd.superproxy.io
INTERACTING_PROXY_PORT=33335
INTERACTING_PROXY_USER=<username>
INTERACTING_PROXY_PASSWORD=<password>
```

The MinIO server is used to store the data and emulate a remote S3 bucket. The `AWS_URL` key must be set to the URL of
the MinIO server. 
When in production mode please remove the `AWS_URL` from the configuration. You may have to rebuild your Docker image for the changes to take effect.
MinIO has not to be configured for the production usage, since the data will be stored in a remote S3 bucket. In the latter case,
please populate all the keys in the `.env` file with the correct values.

## Installation
1. Clone the repository
2. Create the docker containers by running the following command: `make up`
3. Install the required packages using the following command: `make sync-requirements`

**Additional Note**: the `make down` command can be executed to stop the docker container.

## Configuration
The configuration file is located in the `config` folder and is named `config.json`. The configuration file contains the parameters
to be used in the pipeline. Each main key of the JSON file represents the configuration of a different scraper.
The name of the key is the name of the scraper and the value is a dictionary containing the Pydantic model of the scraper
configuration. For more examples, please take a look to the already implemented scrapers and their configurations.

## Usage

### Local testing
For the usage with testing purposes, please create a `.env` file in the root of the project as per the [Pre-requisites](#pre-requisites)
section. Then, you can run the following command to execute the pipeline:
```bash
make up
make run
```

The command `make up` will start the docker containers and `make run` will execute the pipeline. The docker containers
are locally required, since a MinIO server is used to store the data and emulate a remote S3 bucket.
Every time the pipeline is executed, the data are stored into the MinIO server. **Additional Notes**:
- the `make up` command must be executed only once, since the docker container is started and the
MinIO server is started
- the `make run` command can be executed multiple times to run the pipeline.

#### Command Arguments
It is possible to specify the name(s) of the scraper(s) to be executed by adding the `--scrapers` parameter to the
`make run` command. E.g.:
```bash
make run args="--scrapers IOPScraper"
```
or
```bash
make run args="--scrapers IOPScraper SpringerScraper"
```

If you want to force the **entire execution** of one or more scrapers, even when they have been completed, you can add
the `--force` parameter to the `make run` command. E.g.:
```bash
make run args="--scrapers IOPScraper --force"
```

The parameter `--resume` can be added to the `make run` command to resume **only** the failed URLs of the last execution of
the pipeline. This parameter can be composed with `--scrapers`, e.g.:
```bash
make run args="--scrapers IOPScraper --resume"
```

The parameter `--resume-upload` can be added to the `make run` command to resume **only** the failed uploads of the last
execution of the pipeline. This parameter can be composed with `--scrapers`, e.g.:
```bash
make run args="--scrapers IOPScraper --resume-upload"
```

Finally, if you want to retrieve the statistics of the last execution of the pipeline, you can add the `--analytics-only`
parameter (please, check the [Analytics: HowTo](#analytics-howto) section for more details).

**Additional Note**: the `--resume` and `--resume-upload` parameters cannot be used together.

### Production
For the usage with productive purposes, please create a `.env` file in the root of the project as per the [Pre-requisites](#pre-requisites) section. 
Please, contact the maintainer of the project to get the correct values for the keys in the `.env` file.
Run the `pod.sh` script to install the required packages and deploy the infrastructure in the remote Linux-based POD.
```bash
sh pod.sh
```

Then, you can run the pipeline as described in the previous section, but with the following commands:
```bash
make runpod
```
The `make runpod` command will execute the pipeline, similarly to the `make run` command for the local usage. The command `make runpod`
has the same parameters as the `make run` command.

## HowTo: add a new Scraper
In order to add a new scraper, the following steps are required:
1. Create a new file in the `scraper` folder with the name of the scraper. E.g.: `new_editor_scraper.py`
2. If you need to add custom Pydantic model(s), please create a Python file in the `model` folder. E.g.: `new_editor_models.py`
3. Implement a new Pydantic model, representing the configuration of the new scraper, in the Python file previously
created (point 2.) by extending the `BaseConfig` class. If you need enumerators, please extend `Enum` from the `base_enum` module.
4. Implement a new class in the file created at the 1st step. The class must inherit from the `BaseScraper` class and
implement the due methods / properties:
   - `config_model_type`: a `@property` returning the Pydantic model of the configuration of the scraper
   - `scrape`: a method that scrapes the website and returns the data
   - `post_process`: a method that post-processes the data scraped and returns a list of strings representing the URLs of the files to be downloaded / uploaded to the storage
5. Enrich the `config/config.json` file with the JSON-formatted configuration of the new scraper. Please, pay attention
that the key of the JSON object must be the name of the scraper and the value must be the Pydantic model of the configuration. Specifically, the JSON object must contain the following
keys:
   - `bucket_key`: the key of the bucket where the data will be stored
   - `base_url`: the key returning the base URL of the website to be scraped (optional)
   - `cookie_selector`: the key containing the CSS selector of the cookie banner to be clicked, if any, or an empty string if the website does not have a cookie banner (optional)
   - `files_by_request`: whether the files should be retrieved by either usual HTTP request or by scraping (default `True`)

## Analytics: HowTo
At the end of each Scraper, the pipeline will store some statistics in the `scraper_analytics` table of the database.
The statistics are stored in a JSON-formatted string, per scraper. The JSON-formatted string contains the following keys:
- `scraped`, i.e., the analysed URLs
- `content_retrieved`: i.e., those resources successfully collected during the scraping, grouped according to whether
their contents were finally retrieved from the remote URLs
- `uploaded`: i.e., those resources successfully collected during the scraping and which contents were finally retrieved
from the remote URLs, with the result of the upload to the remote storage

The latest statistics can be retrieved by running the following command:
```bash
make run args="--analytics-only"
```

The command will print the statistics of the last execution of the pipeline. If you want to restrict the retrieval
of the statistics to specific scraper(s), you can add the `--scrapers` parameter to the command. E.g.:
```bash
make run args="--analytics-only --scrapers IOPScraper"
```
