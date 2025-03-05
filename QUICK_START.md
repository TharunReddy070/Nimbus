# Cloud Case Study Scraper - Quick Start Guide

This guide will help you get the Cloud Case Study Scraper up and running quickly.

## Prerequisites

- Python 3.9 or later
- Docker and Docker Compose (optional, for containerized deployment)
- Git (optional, for cloning the repository)

## Option 1: Local Setup (Python)

1. **Clone the repository** (if you haven't already):
   ```bash
   git clone https://github.com/yourusername/cloud-case-study-scraper.git
   cd cloud-case-study-scraper
   ```

2. **Run the setup script**:
   - On Linux/Mac:
     ```bash
     chmod +x setup.sh
     ./setup.sh
     ```
   - On Windows:
     ```
     setup.bat
     ```

3. **Start the API server**:
   ```bash
   python api.py
   ```

4. **Access the API**:
   - Open http://localhost:8080/docs in your browser to see the Swagger UI
   - Test the endpoints using the Swagger UI or curl commands

## Option 2: Docker Setup

1. **Clone the repository** (if you haven't already):
   ```bash
   git clone https://github.com/yourusername/cloud-case-study-scraper.git
   cd cloud-case-study-scraper
   ```

2. **Build and run with Docker Compose**:
   ```bash
   docker-compose up --build
   ```

3. **Access the API**:
   - Open http://localhost:8080/docs in your browser to see the Swagger UI
   - Test the endpoints using the Swagger UI or curl commands

## Running Scraping Jobs

### Using the API

1. **Start a scraping job for AWS**:
   ```bash
   curl -X POST "http://localhost:8080/scrape?provider=aws&max-pages=3"
   ```

2. **Start a scraping job for GCP**:
   ```bash
   curl -X POST "http://localhost:8080/scrape?provider=gcp&max-pages=2"
   ```

3. **Start an embedding job**:
   ```bash
   curl -X POST "http://localhost:8080/embed"
   ```

### Using the Command Line

1. **Run the scheduler as a service**:
   ```bash
   python scheduler.py --service
   ```

2. **Run immediate scraping for all providers**:
   ```bash
   python scheduler.py --scrape
   ```

3. **Run immediate scraping for a specific provider**:
   ```bash
   python scheduler.py --scrape --provider aws
   ```

4. **Run immediate embedding**:
   ```bash
   python scheduler.py --embed
   ```

## Viewing Results

1. **Check the logs**:
   - `logs/aws_scraper.log` for AWS scraping logs
   - `logs/gcp_scraper.log` for GCP scraping logs
   - `logs/scheduler.log` for scheduler logs

2. **View case studies in the database**:
   ```bash
   python AWS_casestudies.py --display
   ```

3. **View case studies for a specific provider**:
   ```bash
   python AWS_casestudies.py --display aws
   ```

## Next Steps

- For detailed deployment instructions, see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- For cloud deployment instructions, see [CLOUD_DEPLOYMENT.md](CLOUD_DEPLOYMENT.md)
- For a complete overview of the project, see [README.md](README.md) 