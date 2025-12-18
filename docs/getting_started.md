# Getting Started

This guide will help you set up and run the Data Scraping pipeline on your local machine or in production.

## Prerequisites

Before you begin, ensure you have the following installed:

- Python 3.8+
- Docker and Docker Compose
- Make

## Local Development Setup

### 1. Create Virtual Environment

Create a virtual environment in the `venv` folder:

```bash
python3 -m venv venv
```

Activate the virtual environment:

```bash
source venv/bin/activate
```

### 2. Environment Configuration

Create a `.env` file in the root of the project with the following content:

```bash
# AWS/MinIO Configuration
AWS_URL=http://minio:9100
AWS_REGION=us-east-1
AWS_ACCESS_KEY=minio
AWS_SECRET_KEY=minio1234
AWS_BUCKET_NAME=esa-eve
AWS_MAIN_FOLDER=raw_data

MINIO_URL=http://minio:9100

# Browser Configuration
HEADLESS_BROWSER=true
XVFB_MODE=false

# Database Configuration
DB_HOST=mysql
DB_PORT=3306
DB_NAME=esa_eve
DB_USER=root
DB_PASSWORD=root

# Proxy Configuration (optional)
INTERACTING_PROXY_HOST=brd.superproxy.io
INTERACTING_PROXY_PORT=33335
INTERACTING_PROXY_USER=<username>
INTERACTING_PROXY_PASSWORD=<password>
```

#### Configuration Notes

**MinIO for Local Development**:

  - The MinIO server emulates a remote S3 bucket for local testing
  - The `AWS_URL` key must be set to the URL of the MinIO server
  - For production, remove the `AWS_URL` from the configuration to use real AWS S3

**Browser Settings**:

  - `HEADLESS_BROWSER=true`: Run browser without GUI (recommended for servers)
  - `XVFB_MODE=true`: Use virtual frame buffer (required for headless Linux servers)

**Proxy Settings** (optional):

  - Required only for accessing restricted content
  - Contact the project maintainer for proxy credentials

### 3. Installation

Start the Docker containers:

```bash
make up
```

Install required Python packages:

```bash
make sync-requirements
```

### 4. Verify Installation

Check that all containers are running:

```bash
docker ps
```

You should see containers for:

  - MinIO (S3-compatible storage)
  - MySQL (database)
  - The scraping application

## Running the Pipeline

### Basic Usage

Run all configured scrapers:

```bash
make run
```

The pipeline will:

  1. Connect to MinIO and MySQL
  2. Execute all scrapers defined in `config/config.json`
  3. Store scraped data in MinIO
  4. Track progress in MySQL database

### Running Specific Scrapers

Execute one or more specific scrapers:

```bash
# Run a single scraper
make run args="--scrapers IOPScraper"

# Run multiple scrapers
make run args="--scrapers IOPScraper SpringerScraper"
```

### Force Re-execution

Force complete re-execution of a scraper (even if already completed):

```bash
make run args="--scrapers IOPScraper --force"
```

### Resume Failed Operations

Resume only the failed URLs from the last execution:

```bash
make run args="--scrapers IOPScraper --resume"
```

Resume only the failed uploads from the last execution:

```bash
make run args="--scrapers IOPScraper --resume-upload"
```

**Note**: The `--resume` and `--resume-upload` parameters cannot be used together.

### View Analytics

Retrieve statistics from the last execution:

```bash
make run args="--analytics-only"

# For specific scrapers
make run args="--analytics-only --scrapers IOPScraper"
```

## Production Deployment

### 1. Production Environment Setup

Create a production `.env` file with real credentials:

```bash
# AWS Configuration (remove AWS_URL for production S3)
AWS_REGION=<region>
AWS_ACCESS_KEY=<access-key>
AWS_SECRET_KEY=<secret-key>
AWS_BUCKET_NAME=<bucket-name>
AWS_MAIN_FOLDER=<folder-path>

# Database Configuration
DB_HOST=<database-host>
DB_PORT=3306
DB_NAME=<database-name>
DB_USER=<database-user>
DB_PASSWORD=<database-password>

# Browser Configuration
HEADLESS_BROWSER=true
XVFB_MODE=true

# Proxy Configuration (if needed)
INTERACTING_PROXY_HOST=<proxy-host>
INTERACTING_PROXY_PORT=<proxy-port>
INTERACTING_PROXY_USER=<proxy-username>
INTERACTING_PROXY_PASSWORD=<proxy-password>
```

Contact the project maintainer to obtain production credentials.

### 2. Deploy to Production POD

Run the deployment script on your Linux-based POD:

```bash
sh pod.sh
```

This script will:

  - Install required packages
  - Set up the environment
  - Configure the infrastructure

### 3. Run in Production

Execute the pipeline in production:

```bash
make runpod

# With arguments
make runpod args="--scrapers IOPScraper"
```

The `make runpod` command supports all the same parameters as `make run`.

## Configuration

### Scraper Configuration

Scrapers are configured in `config/config.json`. Each scraper has its own configuration entry:

```json
{
  "ScraperName": {
    "bucket_key": "{main_folder}/subfolder",
    "base_url": "https://example.com",
    "cookie_selector": "button#accept-cookies",
    "files_by_request": true,
    "sources": [
      {
        "url": "https://example.com/articles",
        "type": "journal"
      }
    ]
  }
}
```

Key configuration parameters:

  - `bucket_key`: S3 path where data will be stored
  - `base_url`: Base URL of the website (optional)
  - `cookie_selector`: CSS selector for cookie banner (optional)
  - `files_by_request`: Whether to retrieve files via HTTP request vs scraping (default: `true`)
  - `sources`: List of URLs or configurations to scrape

For detailed configuration examples, see the [Scrapers](scrapers.md) documentation.

## Common Commands

| Command | Description |
|---------|-------------|
| `make up` | Start Docker containers |
| `make down` | Stop Docker containers |
| `make run` | Run pipeline locally |
| `make runpod` | Run pipeline in production |
| `make sync-requirements` | Install Python packages |

## Troubleshooting

### Docker Issues

If containers fail to start:

```bash
# Stop all containers
make down

# Remove volumes
docker-compose down -v

# Restart
make up
```

### Database Connection Issues

Verify MySQL is running:

```bash
docker ps | grep mysql
```

Check database logs:

```bash
docker logs <mysql-container-id>
```

### MinIO Access Issues

Access MinIO console at `http://localhost:9100` with credentials from `.env`:

  - Username: `minio`
  - Password: `minio1234`

### Browser/Selenium Issues

If you encounter browser-related errors:

1. Ensure `HEADLESS_BROWSER=true` in `.env`
2. For Linux servers, set `XVFB_MODE=true`
3. Check that SeleniumBase is properly installed

## Analytics

At the end of each scraper execution, the pipeline stores statistics in the `scraper_analytics` table. The statistics include:

- **scraped**: The analyzed URLs
- **content_retrieved**: Resources successfully collected, grouped by whether their contents were retrieved
- **uploaded**: Resources successfully collected and uploaded to remote storage

View the latest statistics:

```bash
make run args="--analytics-only"

# For specific scrapers
make run args="--analytics-only --scrapers IOPScraper"
```

## Next Steps

- Learn about available scrapers in the [Scrapers](scrapers.md) documentation
- Explore data models in the [Model](model.md) documentation
- See usage examples in the [Examples](examples.md) page
- Learn how to add a new scraper in the [Scrapers](scrapers.md#adding-a-new-scraper) documentation