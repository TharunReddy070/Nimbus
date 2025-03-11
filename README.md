# Cloud Case Study Scraper and Processor

This project automatically scrapes cloud provider case studies, processes them, and stores them in a database for further analysis and embedding. Currently supports AWS, Google Cloud Platform (GCP), and Microsoft Azure.

## Features

- Automatically scrapes case studies from cloud provider websites
- Organizes data by provider (AWS, GCP, Azure, etc.)
- Extracts text content from PDFs
- Stores data in SQLite database with the newest entries appearing first
- Supports vector embedding for AI/ML applications
- Comprehensive logging throughout the scraping process
- Docker containerization for easy deployment
- Cloud Storage integration for data persistence
- FastAPI web service for triggering operations

## Directory Structure

```
project/
├── AWS/              # AWS-specific files
│   ├── PDF/          # PDF files for AWS case studies
│   └── TXT/          # Text files for AWS case studies
├── GCP/              # Google Cloud-specific files
│   ├── PDF/          # PDF files for GCP case studies
│   └── TXT/          # Text files for GCP case studies
├── AZURE/            # Microsoft Azure-specific files
│   ├── PDF/          # PDF files for Azure case studies
│   └── TXT/          # Text files for Azure case studies
├── backup/           # Backup directory
│   ├── aws/          # AWS backup files including CSV links
│   ├── gcp/          # GCP backup files including CSV links
│   └── azure/        # Azure backup files including CSV links
└── database/         # SQLite database
```

## Setup

### Local Development

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Install Playwright browser:
   ```
   python -m playwright install chromium
   ```

### Docker Deployment

1. Build and run with Docker Compose:
   ```
   docker-compose up --build
   ```

2. For detailed deployment instructions to Google Cloud Run, see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md).

## Usage

### API Endpoints

The service exposes the following endpoints:

- `GET /`: Root endpoint, returns API status
- `GET /health`: Health check endpoint
- `POST /scrape`: Trigger scraping process
  - Query parameters:
    - `provider`: Cloud provider (aws, gcp, or azure)
    - `max_pages`: Maximum page number to scrape (default: 3 for AWS, 2 for GCP, 3 for Azure)
- `POST /embed`: Trigger embedding process
  - Query parameters:
    - `provider`: Cloud provider (aws, gcp, or azure)
    - `batch_size`: Number of case studies to embed (default: 10)
- `GET /sync`: Manually trigger a sync with cloud storage
- `GET /schedule`: Start the scheduled jobs

### Automatic Scheduling

The scheduler is configured to run automatically:
- AWS Scraping: Daily at 2:00 AM (up to page 3)
- GCP Scraping: Daily at 3:00 AM (up to page 2)
- Azure Scraping: Daily at 4:00 AM (up to page 3)
- Embedding: Temporarily disabled until embedding logic is implemented

The automatic service is optimized to check a reasonable number of pages for each provider since we're running daily and only a few new case studies would typically be added each day.

### Data Processing Workflow

All cloud provider implementations follow the same workflow pattern:

1. **Link Extraction**:
   - Links are scraped from provider websites
   - Each link is stored in a CSV file in the backup directory (`backup/aws/aws_case_study_links.csv`, `backup/gcp/gcp_case_study_links.csv`, or `backup/azure/azure_case_study_links.csv`)
   - The CSV includes:
     - `page_number`: The page where the link was found
     - `link`: The URL of the case study
     - `is_processed`: Flag indicating if the case study has been processed (initially `False`)
   - For AWS: Scrapes from the specified start page up to the max page number
   - For GCP: When run directly, skips the first 18 links (6 video links and 12 case study links) from the initial page load; when run from the scheduler, includes all links
   - For Azure: Scrapes from page 1 up to the max page number, extracting links from "Read story" buttons

2. **Case Study Processing**:
   - The processor reads the CSV file from the backup directory and processes only unprocessed case studies
   - For each case study:
     - Downloads the case study as a PDF to the provider's PDF directory (`AWS/PDF/`, `GCP/PDF/`, or `AZURE/PDF/`)
     - Saves the link as a text file in the provider's TXT directory (`AWS/TXT/`, `GCP/TXT/`, or `AZURE/TXT/`)
     - Extracts text content from the PDF using PyPDF2
     - Saves the content to the database with fields:
       - `id`: Unique identifier
       - `provider`: Cloud provider (aws, gcp, azure)
       - `link`: Original URL
       - `pdf_path`: Path to the saved PDF file
       - `txt_path`: Path to the text file containing the link
       - `content`: Extracted text content
       - `is_embedded`: Flag indicating if the case study has been embedded (initially `0`)
     - Updates the `is_processed` flag to `True` in the CSV file
   - If any error occurs during processing, the case study is still marked as processed (`is_processed = True`) to prevent repeated attempts on problematic links

3. **Embedding**:
   - The embedding process reads unembedded case studies from the database
   - Processes them with an embedding model
   - Updates the `is_embedded` flag to `1` in the database

This consistent workflow ensures that all cloud provider case studies are processed in the same way, making the system easier to maintain and extend.

### Command Reference

#### Direct Script Usage (Local Development Only)

##### Scheduler Commands

| Command | Description |
|---------|-------------|
| `python scheduler.py --service` | Run the scheduler as a service. This starts the automated scheduler that will run scraping and embedding jobs at configured times. |
| `python scheduler.py --scrape` | Run immediate scraping for all providers. This scrapes case studies from all configured providers (AWS, GCP, Azure) using default settings. |
| `python scheduler.py --scrape --provider aws` | Run immediate scraping for AWS only. This scrapes case studies only from AWS using default settings (up to page 3). |
| `python scheduler.py --scrape --provider gcp` | Run immediate scraping for GCP only. This scrapes case studies only from Google Cloud Platform using default settings (up to page 2). |
| `python scheduler.py --scrape --provider azure` | Run immediate scraping for Azure only. This scrapes case studies only from Microsoft Azure using default settings (up to page 3). |
| `python scheduler.py --scrape --max-pages 10` | Run immediate scraping with custom page limit. This scrapes up to page 10 for each provider. |
| `python scheduler.py --scrape --provider aws --max-pages 5` | Run immediate scraping for AWS with custom page limit. This scrapes up to page 5 of AWS case studies. |
| `python scheduler.py --embed` | Run immediate embedding for all providers. This processes all unembedded case studies from all providers and marks them as embedded. |
| `python scheduler.py --embed --provider aws` | Run immediate embedding for AWS only. This processes only unembedded AWS case studies and marks them as embedded. |
| `python scheduler.py --embed --batch-size 20` | Run immediate embedding with custom batch size. This processes up to 20 unembedded case studies from each provider. |
| `python scheduler.py --embed --provider aws --batch-size 10` | Run immediate embedding for AWS with custom batch size. This processes up to 10 unembedded AWS case studies. |

##### Case Study Display Commands

| Command | Description |
|---------|-------------|
| `python AWS_casestudies.py --display` | Display all case studies from all providers, sorted with newest first. |
| `python AWS_casestudies.py --display aws` | Display only AWS case studies, sorted with newest first. |
| `python AWS_casestudies.py --display gcp` | Display only GCP case studies, sorted with newest first. |
| `python AWS_casestudies.py --display azure` | Display only Azure case studies, sorted with newest first. |
| `python AWS_casestudies.py --display --limit 10` | Display the 10 most recent case studies from all providers. |
| `python AWS_casestudies.py --display aws --limit 5` | Display the 5 most recent AWS case studies. |

##### Direct Provider Commands

| Command | Description |
|---------|-------------|
| `python AWS_links.py` | Run the AWS scraper directly to extract links from pages 2-3 (default). |
| `python AWS_links.py --start-page 2 --max-pages 5` | Run the AWS scraper directly to extract links from pages 2-5. |
| `python gcloud_links.py` | Run the GCP scraper directly to extract links up to page 2 (default). When run directly, skips the first 18 links. |
| `python gcloud_links.py 3` | Run the GCP scraper directly to extract links up to page 3. When run directly, skips the first 18 links. |
| `python azure_links.py` | Run the Azure scraper directly to extract links from pages 1-3 (default). |
| `python azure_links.py 5` | Run the Azure scraper directly to extract links up to page 5. |
| `python azure_links.py 5 2` | Run the Azure scraper directly to extract links from pages 2-5. |
| `python gcloud_casestudies.py` | Process GCP case studies directly. This will process only unprocessed case studies. |
| `python azure_casestudies.py` | Process Azure case studies directly. This will process only unprocessed case studies. |

## Understanding Page Numbering

### AWS Scraper
- For AWS, pages are numbered sequentially on the AWS website
- `start_page` (default: 2) is the first page to scrape
- `max_pages` (default: 3) is the maximum page number to scrape up to (inclusive)
- Example: With default settings, the scraper will extract links from pages 2 and 3

### GCP Scraper
- For GCP, page 1 refers to the initial page load
- Subsequent pages are loaded by clicking the "More" button
- `max_pages` (default: 2) is the maximum page number to reach
- Example: With default settings, the scraper will extract links from the initial page load (page 1) and after one "More" button click (page 2)
- When run directly, the scraper skips the first 18 links from the initial page load (6 video links and 12 case study links)
- When run from the scheduler, all links are included

### Azure Scraper
- For Azure, pages are numbered sequentially on the Microsoft website
- `start_page` (default: 1) is the first page to scrape
- `max_pages` (default: 3) is the maximum page number to scrape up to (inclusive)
- Example: With default settings, the scraper will extract links from pages 1, 2, and 3
- The scraper extracts links from "Read story" buttons on each case study card

## Logging

The system includes comprehensive logging throughout the scraping process:
- Initialization of scraping with parameters
- Navigation between pages
- Number of links found on each page
- New links added to the CSV file
- Total links found and saved
- Any errors encountered during the process

Logs are saved to:
- `aws_scraper.log` for AWS scraping
- `gcp_scraper.log` for GCP scraping
- `azure_scraper.log` for Azure scraping
- `azure_processor.log` for Azure case study processing
- `scheduler.log` for scheduler operations

## Database Structure

The database stores the following information for each case study:
- `id`: Unique identifier
- `provider`: Cloud provider (aws, gcp, azure, etc.)
- `link`: Original URL
- `pdf_path`: Path to the saved PDF file
- `txt_path`: Path to the text file containing the link
- `content`: Extracted text content
- `is_embedded`: Flag indicating if the case study has been embedded (0=no, 1=yes)
- `created_at`: Timestamp when the record was created

## Files

- `api.py`: FastAPI web service for triggering operations
- `AWS_links.py`: Scrapes case study links from AWS website
- `AWS_casestudies.py`: Processes AWS case studies and extracts content
- `gcloud_links.py`: Scrapes case study links from GCP website
- `gcloud_casestudies.py`: Processes GCP case studies and extracts content
- `azure_links.py`: Scrapes case study links from Azure website
- `azure_casestudies.py`: Processes Azure case studies and extracts content
- `cloud_storage.py`: Manages cloud storage operations
- `db_manager.py`: Manages database operations
- `scheduler.py`: Handles automated scheduling
- `embedding_example.py`: Example script for processing embeddings
- `Dockerfile`: Container definition for Docker deployment
- `docker-compose.yml`: Configuration for local Docker deployment
- `cloudbuild.yaml`: Configuration for Google Cloud Build deployment 