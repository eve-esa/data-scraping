# Data Scraping Pipeline

Welcome to the Data Scraping pipeline documentation. This pipeline is designed to collect and scrape Earth Observation and Earth Science data from various academic publishers, journals, and data sources.


## Features

- **32+ Specialized Scrapers**: Pre-configured scrapers for major publishers and data sources including IEEE, Springer, Elsevier, NASA, ESA, and more
- **Flexible Architecture**: Extensible base classes for creating new scrapers
- **Cloud Storage Integration**: S3-compatible storage (AWS S3, MinIO)
- **Database Tracking**: MySQL database for tracking scraping progress and analytics
- **Docker Support**: Containerized deployment for easy setup
- **Proxy Support**: Built-in proxy support for restricted content
- **Resume Capability**: Resume failed scraping operations
- **Analytics**: Comprehensive statistics on scraping operations

## Quick Start

```bash
# Clone the repository
git clone <repository-url>
cd data-scraping

# Start Docker containers
make up

# Run the pipeline
make run
```

For detailed installation instructions, see the [Getting Started](getting_started.md) page.

## Documentation Structure

- **[Getting Started](getting_started.md)**: Installation, prerequisites, and setup guide
- **[Scrapers](scrapers.md)**: Complete documentation of all available scrapers
- **[Model](model.md)**: Data models and configuration schemas
- **[Examples](examples.md)**: Usage examples and common workflows

## Architecture Overview

The scraping system is built on a hierarchical architecture:

1. **Base Scrapers**: Abstract classes providing core functionality (Selenium, storage, database)
2. **Specialized Scrapers**: Publisher-specific implementations
3. **Configuration**: JSON-based configuration for each scraper
4. **Storage**: S3-compatible storage for collected data
5. **Database**: MySQL for tracking progress and analytics

## Funding

This project is supported by the European Space Agency (ESA) Φ-lab through the Large Language Model for Earth Observation and Earth Science project, as part of the Foresight Element within FutureEO Block 4 programme.

## License

This project is released under the Apache 2.0 License.

## Contributing

We welcome contributions! Please open an issue or submit a pull request on GitHub to help improve the pipeline.
