# Examples

This page provides practical examples and common workflows for using the Data Scraping pipeline.

## Basic Usage Examples

### Running a Single Scraper

Run a specific scraper to collect data from one source:

```bash
make run args="--scrapers IOPScraper"
```

**What happens:**

  1. The pipeline loads configuration from `config/config.json`
  2. IOPScraper is initialized with its configuration
  3. The scraper navigates to configured URLs
  4. PDF links are extracted and downloaded
  5. Files are uploaded to MinIO/S3
  6. Results are logged to the database

### Running Multiple Scrapers

Execute several scrapers sequentially:

```bash
make run args="--scrapers IOPScraper SpringerScraper MDPIScraper"
```

This will run each scraper one after another, useful for collecting data from multiple sources in one command.

### Running All Scrapers

Execute all configured scrapers:

```bash
make run
```

This processes all scrapers defined in `config/config.json`.

## Advanced Usage

### Force Re-execution

Force a scraper to run again even if it completed successfully before:

```bash
make run args="--scrapers IOPScraper --force"
```

**Use cases:**

  - Testing after code changes
  - Collecting new content from the same source
  - Recovering from incomplete runs

### Resume Failed URLs

Resume only failed URLs from the previous execution:

```bash
make run args="--scrapers IOPScraper --resume"
```

**When to use:**

  - Network errors occurred during scraping
  - Some pages were temporarily unavailable
  - Timeout errors on specific URLs

**What it does:**

  - Queries `scraper_failure` table for failed URLs
  - Re-attempts only those URLs
  - Updates success/failure status

### Resume Failed Uploads

Resume only failed file uploads:

```bash
make run args="--scrapers IOPScraper --resume-upload"
```

**When to use:**

  - S3/MinIO connection issues occurred
  - Upload timeouts for large files
  - Storage quota was exceeded

**Important:** Cannot combine `--resume` and `--resume-upload` in one command.

## Analytics Examples

### View All Scraper Statistics

Get analytics for all scrapers:

```bash
make run args="--analytics-only"
```

**Output includes:**

  - URLs scraped
  - Content successfully retrieved
  - Files uploaded to storage
  - Failure counts

### View Specific Scraper Statistics

Get analytics for specific scrapers:

```bash
make run args="--analytics-only --scrapers IOPScraper SpringerScraper"
```

### Understanding Analytics Output

The analytics JSON contains:

```json
{
  "scraped": {
    "total": 100,
    "successful": 95,
    "failed": 5
  },
  "content_retrieved": {
    "retrieved": 90,
    "not_retrieved": 5
  },
  "uploaded": {
    "successful": 88,
    "failed": 2
  }
}
```

**Metrics explained:**

  - **scraped**: URLs processed by the scraper
  - **content_retrieved**: Resources whose content was successfully downloaded
  - **uploaded**: Resources successfully uploaded to S3

## Configuration Examples

### Simple Publisher Configuration

For a straightforward journal website:

```json
{
  "SimplePublisherScraper": {
    "bucket_key": "{main_folder}/simple_publisher",
    "base_url": "https://journal.example.com",
    "cookie_selector": "button.accept-cookies",
    "sources": [
      {
        "url": "https://journal.example.com/volume/1/issue/1",
        "type": "issue_or_collection"
      }
    ]
  }
}
```

### Iterative Journal Configuration

For journals with volume/issue structure:

```json
{
  "JournalScraper": {
    "bucket_key": "{main_folder}/journal",
    "journals": [
      {
        "url": "https://journal.com",
        "name": "Journal of Earth Observation",
        "start_volume": 1,
        "end_volume": 20,
        "start_issue": 1,
        "end_issue": 12,
        "consecutive_missing_volumes_threshold": 3,
        "consecutive_missing_issues_threshold": 3
      }
    ]
  }
}
```

**Parameters:**

  - `start_volume/end_volume`: Volume range to scrape
  - `start_issue/end_issue`: Issue range per volume
  - `consecutive_missing_*_threshold`: Stop after N consecutive missing volumes/issues

### Pagination Configuration

For search results with pagination:

```json
{
  "SearchScraper": {
    "bucket_key": "{main_folder}/search",
    "base_url": "https://publisher.com",
    "sources": [
      {
        "landing_page_url": "https://publisher.com/search?q=remote+sensing&page={page_number}",
        "page_size": 50,
        "max_allowed_papers": 1000
      }
    ]
  }
}
```

**Parameters:**

  - `{page_number}`: Placeholder for page number (auto-incremented)
  - `page_size`: Results per page
  - `max_allowed_papers`: Maximum papers to collect

### Multi-Source Configuration

For scrapers with multiple sub-sources:

```json
{
  "MultiSourceScraper": {
    "bucket_key": "{main_folder}/multi",
    "sources": [
      {
        "name": "Source A",
        "scraper": "SubScraperA",
        "config": {
          "base_url": "https://source-a.com",
          "cookie_selector": "button.accept"
        }
      },
      {
        "name": "Source B",
        "scraper": "SubScraperB",
        "config": {
          "base_url": "https://source-b.com",
          "urls": ["https://source-b.com/papers"]
        }
      }
    ]
  }
}
```

### Direct Download Configuration

For known PDF URLs:

```json
{
  "DirectLinksScraper": {
    "bucket_key": "{main_folder}/direct",
    "sources": [
      {
        "name": "Example PDFs",
        "config": {
          "bucket_key": "custom_folder",
          "urls": [
            "https://example.com/paper1.pdf",
            "https://example.com/paper2.pdf",
            "https://example.com/paper3.pdf"
          ]
        }
      }
    ]
  }
}
```

## Debugging Examples

### Check Scraper Status

View database status for a scraper:

```sql
-- Connect to MySQL
docker exec -it <mysql-container> mysql -u root -p

-- Check completed scrapers
SELECT scraper, created_at FROM scraper_output;

-- Check failed URLs
SELECT scraper, url, error FROM scraper_failure ORDER BY created_at DESC LIMIT 10;

-- Check uploaded resources
SELECT COUNT(*) as total FROM uploaded_resource;
```

### Inspect MinIO Storage

Access MinIO console:

```bash
# Local: http://localhost:9100
# Login: minio / minio1234
```

Navigate to your bucket and verify files were uploaded correctly.

### View Scraper Logs

Check Docker logs for errors:

```bash
# View recent logs
docker logs <container-name> --tail 100

# Follow logs in real-time
docker logs -f <container-name>

# Search for errors
docker logs <container-name> 2>&1 | grep ERROR
```

### Test Configuration

Validate configuration before running:

```python
# In Python console
from model.iop_models import IOPConfig
import json

with open('config/config.json') as f:
    config = json.load(f)

# Validate configuration
iop_config = IOPConfig(**config['IOPScraper'])
print(iop_config)
```

## Troubleshooting Examples

### Handle Cookie Banners

If scraper fails due to cookie banners:

1. Inspect the page in browser
2. Find the "Accept" button CSS selector
3. Add to configuration:

```json
{
  "ScraperName": {
    "cookie_selector": "button#onetrust-accept-btn-handler",
    ...
  }
}
```

### Handle Dynamic Loading

For JavaScript-loaded content:

```python
# In your scraper's scrape() method

# Wait for element to load
self._driver.wait_for_element("div.article-list", timeout=10)

# Or use loading tag
# Configure in config.json:
{
  "loading_tag": "div.loading-spinner"
}
```

### Handle Pagination Edge Cases

For pagination that doesn't follow standard patterns:

```python
# In your scraper

page_number = 1
while True:
    url = f"https://example.com/search?page={page_number}"
    self._driver.open(url)

    # Check if results exist
    results = self._driver.find_elements("div.result")
    if not results:
        break  # No more pages

    # Process results
    # ...

    page_number += 1
```

### Handle Proxy Requirements

For sites requiring proxy:

```json
{
  "ScraperName": {
    "request_with_proxy": true,
    ...
  }
}
```

Ensure proxy credentials are in `.env`:

```bash
INTERACTING_PROXY_HOST=proxy.example.com
INTERACTING_PROXY_PORT=8080
INTERACTING_PROXY_USER=username
INTERACTING_PROXY_PASSWORD=password
```

## Performance Optimization

### Parallel Scraping

Run multiple scrapers in parallel using separate processes:

```bash
# Terminal 1
make run args="--scrapers IOPScraper MDPIScraper" &

# Terminal 2
make run args="--scrapers SpringerScraper ElsevierScraper" &
```

**Note:** Ensure each scraper targets different domains to avoid rate limiting.

### Optimize Page Size

For pagination scrapers, adjust page size:

```json
{
  "sources": [
    {
      "landing_page_url": "...",
      "page_size": 100  // Larger pages = fewer requests
    }
  ]
}
```

**Balance:** Larger pages are faster but may timeout.

### Limit Paper Count

To avoid excessive scraping:

```json
{
  "sources": [
    {
      "landing_page_url": "...",
      "max_allowed_papers": 5000
    }
  ]
}
```

## Integration Examples

### Query Uploaded Resources

After scraping, query the database:

```python
from repository.uploaded_resource_repository import UploadedResourceRepository

repo = UploadedResourceRepository()

# Get all resources from a specific scraper
resources = repo.get_all_by({"source": "IOPScraper"})

for resource in resources:
    print(f"URL: {resource.url}")
    print(f"S3 Key: {resource.s3_key}")
    print(f"SHA256: {resource.sha256}")
```

### Download from S3

Retrieve scraped files from S3:

```python
from service.storage import S3Storage

s3 = S3Storage()

# Download a file
s3_key = "raw_data/iopscience/paper.pdf"
local_path = "/tmp/paper.pdf"

s3.download_file(s3_key, local_path)
```

### Export Analytics

Export analytics to CSV:

```bash
# Get analytics as JSON
make run args="--analytics-only --scrapers IOPScraper" > analytics.json

# Process with Python
python -c "
import json
import csv

with open('analytics.json') as f:
    data = json.load(f)

with open('analytics.csv', 'w') as f:
    writer = csv.writer(f)
    writer.writerow(['Metric', 'Value'])
    for key, value in data.items():
        writer.writerow([key, value])
"
```
