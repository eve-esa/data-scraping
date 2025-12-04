# Scrapers

This section documents all available scrapers in the project for collecting Earth Observation and Remote Sensing data from various academic publishers, journals, and data sources.

## Overview

The scraping system is designed around a hierarchical class structure where specialized scrapers inherit from base classes that provide common functionality. Each scraper is configured via `config/config.json` and targets specific publishers or data sources.

### Configured Scrapers

The following table lists all scrapers currently configured in the system:

| Scraper | Base URL | Storage Folder | Description |
|---------|----------|----------------|-------------|
| **IOPScraper** | `https://iopscience.iop.org` | `{main_folder}/iopscience` | IOP Science journal articles and issues |
| **MDPIScraper** | `https://www.mdpi.com` | `{main_folder}/mdpi` | MDPI journals including Remote Sensing, Geosciences, Atmosphere |
| **SpringerScraper** | `https://link.springer.com` | `{main_folder}/springer` | Springer journals, books, and search results |
| **AMSScraper** | `https://journals.ametsoc.org` | `{main_folder}/ams` | American Meteorological Society publications |
| **CopernicusScraper** | Multiple Copernicus journals | `{main_folder}/copernicus` | 16+ Copernicus open-access journals |
| **CopernicusCatalogueScraper** | `https://www.copernicus.eu/` | `{main_folder}/copernicus` | Copernicus services catalogue |
| **SeosScraper** | `https://seos-project.eu` | `{main_folder}/seos` | SEOS project educational materials |
| **NCBIScraper** | `https://www.ncbi.nlm.nih.gov` | `{main_folder}/ncbi` | NCBI PubMed Central articles |
| **CambridgeUniversityPressScraper** | `https://www.cambridge.org` | `{main_folder}/cambridge_university_press` | Cambridge University Press journals |
| **OxfordAcademicScraper** | `https://academic.oup.com` | `{main_folder}/oxford_academic` | Oxford Academic journals |
| **IEEEScraper** | `https://ieeexplore.ieee.org` | `{main_folder}/ieee` | IEEE Xplore open access articles |
| **TaylorAndFrancisScraper** | `https://www.tandfonline.com` | `{main_folder}/taylor_and_francis` | Taylor & Francis journals |
| **FrontiersScraper** | `https://www.frontiersin.org/` | `{main_folder}/frontiers` | Frontiers in Remote Sensing |
| **SageScraper** | `https://journals.sagepub.com` | `{main_folder}/sage` | SAGE Publications journals |
| **EOGEScraper** | `https://eoge.ut.ac.ir` | `{main_folder}/eoge` | Earth Observations and Geomatics Engineering journal |
| **ArxivScraper** | `https://arxiv.org` | `{main_folder}/arxiv` | arXiv preprints |
| **WileyScraper** | Multiple Wiley domains | `{main_folder}/wiley` | Wiley journals (AGU, EOS, etc.) |
| **EOSScraper** | `https://eos.org/` | `{main_folder}/eos` | EOS Science News archives |
| **ESAScraper** | Multiple ESA domains | `{main_folder}/esa` | ESA Earth Online, EO Portal, Sentiwiki |
| **ElsevierScraper** | `https://www.sciencedirect.com` | `{main_folder}/elsevier` | ScienceDirect open access journals |
| **NASAScraper** | Multiple NASA domains | `{main_folder}/nasa` | NASA EarthData, NTRS, EOS Portal |
| **OpenNightLightsScraper** | `https://worldbank.github.io/OpenNightLights/` | `{main_folder}/open_night_lights_scraper` | World Bank Open Night Lights documentation |
| **WikipediaScraper** | `https://en.wikipedia.org/` | `{main_folder}/wikipedia` | Wikipedia EO-related categories |
| **MITScraper** | `https://ocw.mit.edu/` | `{main_folder}/mit` | MIT OpenCourseWare |
| **JAXAScraper** | `https://earth.jaxa.jp/en/eo-knowledge` | `{main_folder}/jaxa` | JAXA Earth Observation knowledge base |
| **UKMetOfficeScraper** | `https://library.metoffice.gov.uk` | `{main_folder}/uk_met_office` | UK Met Office library |
| **EOAScraper** | `https://www.eoa.org.au/` | `{main_folder}/eoa` | Earth Observation Australia textbooks |
| **ISPRSScraper** | `https://www.isprs.org/` | `{main_folder}/isprs` | ISPRS publication archives |
| **EUMETSATScraper** | Multiple EUMETSAT domains | `{main_folder}/eumetsat` | EUMETSAT documentation and case studies |
| **EarthDataScienceScraper** | `https://www.earthdatascience.org/` | `{main_folder}/earth_data_science` | Earth Data Science tutorials |
| **DirectLinksScraper** | Various | `{main_folder}/miscellaneous` | Direct PDF links from multiple sources |
| **IntechOpenScraper** | `https://www.intechopen.com/` | `{main_folder}/intech_open` | IntechOpen books and chapters |

## Base Scraper Architecture

The scraping system is built on a set of abstract base classes that provide common functionality. Understanding these base classes is essential for extending or modifying the scraping behavior.

### Base Class Descriptions

**BaseScraper**: The root abstract class that all scrapers inherit from. Provides core functionality including Selenium WebDriver management, cookie handling, S3 storage integration, database repository access, and analytics tracking. Every scraper implements the abstract `scrape()` method defined here.

**BaseIterativePublisherScraper**: Designed for publishers that organize content in a journal → volume → issue hierarchy. Iterates through volumes and issues systematically, with support for handling missing volumes/issues using consecutive threshold logic.

**BasePaginationPublisherScraper**: Handles publishers with paginated search results or article listings. Automatically navigates through pages until no more results are found, with configurable page sizes and maximum paper limits.

**BaseUrlPublisherScraper**: Used for publishers where content URLs follow predictable patterns. Processes lists of URLs and extracts content directly without complex navigation.

**BaseMappedPublisherScraper**: For publishers that require mapping between different URL structures or identifiers before scraping content. Provides a two-stage process: first mapping, then scraping.

**BaseCrawlingScraper**: Implements recursive web crawling from a starting URL. Follows links within the same domain and extracts content from all discovered pages. Useful for documentation sites and knowledge bases.

**BaseSourceDownloadScraper**: Specialized for direct file downloads where download URLs are known in advance. Handles PDF and other document formats directly without HTML parsing.



## Adding a New Scraper

To extend the pipeline with a new scraper, follow these steps:

### 1. Create Scraper File

Create a new file in the `scraper` folder with the name of your scraper:

```python
# scraper/new_publisher_scraper.py
from scraper.base_scraper import BaseScraper
from model.new_publisher_models import NewPublisherConfig

class NewPublisherScraper(BaseScraper):
    """
    Scraper for New Publisher website.
    """

    @property
    def config_model_type(self):
        """Return the Pydantic model for configuration."""
        return NewPublisherConfig

    def scrape(self):
        """
        Scrape the website and return scraped data.

        Returns:
            dict: Dictionary containing scraped data
        """
        # Implement your scraping logic here
        # Use self._driver for Selenium operations
        # Use self._config_model to access configuration

        scraped_data = {}

        for source in self._config_model.sources:
            # Navigate to URL
            self._driver.open(source.url)

            # Handle cookies if needed
            if not self._cookie_handled and self._config_model.cookie_selector:
                self._driver.click(self._config_model.cookie_selector)
                self._cookie_handled = True

            # Extract data
            # ... your scraping logic ...

        return scraped_data

    def post_process(self, scraped_data):
        """
        Process scraped data and return URLs to download.

        Args:
            scraped_data: Data returned from scrape()

        Returns:
            List[str]: List of URLs to download/upload
        """
        urls = []

        # Process scraped_data and extract download URLs
        # ... your post-processing logic ...

        return urls
```

### 2. Create Model File (Optional)

If you need custom Pydantic models, create a file in the `model` folder:

```python
# model/new_publisher_models.py
from typing import List
from pydantic import Field
from model.base_models import BaseConfig, BaseSource

class NewPublisherSource(BaseSource):
    """Configuration for a single source."""
    url: str
    type: str = "journal"
    # Add custom fields as needed

class NewPublisherConfig(BaseConfig):
    """Configuration model for NewPublisherScraper."""
    base_url: str
    sources: List[NewPublisherSource]
    # Add any custom configuration fields
    custom_field: str = Field(default="default_value")
```

**Note**: If you need enumerators, extend `Enum` from the `base_enum` module.

### 3. Choose the Right Base Class

Select the appropriate base class for your scraper:

- **BaseScraper**: For custom scraping logic
- **BaseIterativePublisherScraper**: For journal → volume → issue hierarchies
- **BasePaginationPublisherScraper**: For paginated search results
- **BaseUrlPublisherScraper**: For simple URL lists
- **BaseMappedPublisherScraper**: For two-stage mapping and scraping
- **BaseCrawlingScraper**: For recursive web crawling
- **BaseSourceDownloadScraper**: For direct file downloads

Example using `BaseIterativePublisherScraper`:

```python
from scraper.base_iterative_publisher_scraper import BaseIterativePublisherScraper

class NewJournalScraper(BaseIterativePublisherScraper):
    @property
    def config_model_type(self):
        return NewJournalConfig

    def _scrape_journal(self, journal):
        # Implement journal-specific scraping
        pass
```

### 4. Add Configuration to config.json

Add your scraper's configuration to `config/config.json` (you can find more examples [here](examples#configuration-examples)):

```json
{
  "NewPublisherScraper": {
    "bucket_key": "{main_folder}/new_publisher",
    "base_url": "https://newpublisher.com",
    "cookie_selector": "button#accept-cookies",
    "files_by_request": true,
    "sources": [
      {
        "url": "https://newpublisher.com/articles",
        "type": "journal"
      }
    ]
  }
}
```

#### Configuration Keys

**Required:**
- `bucket_key`: S3 storage path (use `{main_folder}` placeholder)

**Optional:**
- `base_url`: Base URL of the website
- `cookie_selector`: CSS selector for cookie banner acceptance button
- `files_by_request`: Whether to download files via HTTP (default: `true`) or scrape them
- `request_with_proxy`: Use proxy for requests (default: `false`)
- `sources`: List of sources to scrape (structure depends on your model)

### 5. Test Your Scraper

Run your new scraper:

```bash
# Run with force to test from scratch
make run args="--scrapers NewPublisherScraper --force"

# Check logs for errors
docker logs <container-id>
```

### 6. Verify Results

Check that data was scraped and uploaded correctly:

1. **MinIO Console**: Visit `http://localhost:9100` and check your bucket
2. **Database**: Query the `scraper_output` and `uploaded_resource` tables
3. **Analytics**: Run `make run args="--analytics-only --scrapers NewPublisherScraper"`

### Example: Complete Simple Scraper

Here's a complete example of a simple scraper:

```python
# scraper/example_scraper.py
from typing import List
from scraper.base_scraper import BaseScraper
from model.base_models import BaseConfig, BaseSource

class ExampleConfig(BaseConfig):
    base_url: str
    sources: List[BaseSource]

class ExampleScraper(BaseScraper):
    @property
    def config_model_type(self):
        return ExampleConfig

    def scrape(self):
        pdf_links = []

        for source in self._config_model.sources:
            self._driver.open(source.url)

            # Find all PDF links
            links = self._driver.find_elements("a[href$='.pdf']")
            for link in links:
                href = link.get_attribute('href')
                if href:
                    pdf_links.append(href)

        return {"pdf_links": pdf_links}

    def post_process(self, scraped_data):
        return scraped_data.get("pdf_links", [])
```

With configuration:

```json
{
  "ExampleScraper": {
    "bucket_key": "{main_folder}/example",
    "base_url": "https://example.com",
    "sources": [
      {"url": "https://example.com/papers"}
    ]
  }
}
```


### Common Selenium Operations

```python
# Open URL
self._driver.open(url)

# Click element
self._driver.click(selector)

# Find elements
elements = self._driver.find_elements(selector)

# Get attribute
href = element.get_attribute('href')

# Get text
text = element.text

# Wait for element
self._driver.wait_for_element(selector)

# Execute JavaScript
self._driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
```



## Code Reference

Below is the detailed API documentation for all scraper classes:

### Base Classes

::: scraper.base_scraper
    options:
      show_root_heading: true
      show_source: false

::: scraper.base_crawling_scraper
    options:
      show_root_heading: true
      show_source: false

::: scraper.base_iterative_publisher_scraper
    options:
      show_root_heading: true
      show_source: false

::: scraper.base_mapped_publisher_scraper
    options:
      show_root_heading: true
      show_source: false

::: scraper.base_pagination_publisher_scraper
    options:
      show_root_heading: true
      show_source: false

::: scraper.base_url_publisher_scraper
    options:
      show_root_heading: true
      show_source: false

::: scraper.base_source_download_scraper
    options:
      show_root_heading: true
      show_source: false

## Publisher Scrapers

::: scraper.ams_scraper
    options:
      show_root_heading: true
      show_source: false

::: scraper.arxiv_scraper
    options:
      show_root_heading: true
      show_source: false

::: scraper.cambridge_university_press_scraper
    options:
      show_root_heading: true
      show_source: false

::: scraper.elsevier_scraper
    options:
      show_root_heading: true
      show_source: false

::: scraper.frontiers_scraper
    options:
      show_root_heading: true
      show_source: false

::: scraper.ieee_scraper
    options:
      show_root_heading: true
      show_source: false

::: scraper.intechopen_scraper
    options:
      show_root_heading: true
      show_source: false

::: scraper.iop_scraper
    options:
      show_root_heading: true
      show_source: false

::: scraper.isprs_scraper
    options:
      show_root_heading: true
      show_source: false

::: scraper.mdpi_scraper
    options:
      show_root_heading: true
      show_source: false

::: scraper.ncbi_scraper
    options:
      show_root_heading: true
      show_source: false

::: scraper.oxford_academic_scraper
    options:
      show_root_heading: true
      show_source: false

::: scraper.sage_scraper
    options:
      show_root_heading: true
      show_source: false

::: scraper.springer_scraper
    options:
      show_root_heading: true
      show_source: false

::: scraper.taylor_and_francis_scraper
    options:
      show_root_heading: true
      show_source: false

::: scraper.wiley_scraper
    options:
      show_root_heading: true
      show_source: false

## Data Source Scrapers

::: scraper.copernicus_catalogue_scraper
    options:
      show_root_heading: true
      show_source: false

::: scraper.copernicus_scraper
    options:
      show_root_heading: true
      show_source: false

::: scraper.direct_links_scraper
    options:
      show_root_heading: true
      show_source: false

::: scraper.earth_data_science_scraper
    options:
      show_root_heading: true
      show_source: false

::: scraper.eoa_scraper
    options:
      show_root_heading: true
      show_source: false

::: scraper.eoge_scraper
    options:
      show_root_heading: true
      show_source: false

::: scraper.eos_scraper
    options:
      show_root_heading: true
      show_source: false

::: scraper.esa_scraper
    options:
      show_root_heading: true
      show_source: false

::: scraper.eumetsat_scraper
    options:
      show_root_heading: true
      show_source: false

::: scraper.jaxa_scraper
    options:
      show_root_heading: true
      show_source: false

::: scraper.mit_scraper
    options:
      show_root_heading: true
      show_source: false

::: scraper.nasa_scraper
    options:
      show_root_heading: true
      show_source: false

::: scraper.open_night_lights_scraper
    options:
      show_root_heading: true
      show_source: false

::: scraper.seos_scraper
    options:
      show_root_heading: true
      show_source: false

::: scraper.uk_met_office_scraper
    options:
      show_root_heading: true
      show_source: false

::: scraper.wikipedia_scraper
    options:
      show_root_heading: true
      show_source: false
