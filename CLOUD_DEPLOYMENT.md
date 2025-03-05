# Cloud Case Study Scraper - Cloud Deployment Guide

This guide explains how to deploy the Cloud Case Study Scraper to Google Cloud Run using Docker.

## Overview

The Cloud Case Study Scraper is containerized using Docker and can be deployed to Google Cloud Run for a serverless, scalable deployment. The application includes:

- FastAPI web service for triggering scraping and embedding
- Cloud Storage integration for data persistence
- Cloud Scheduler integration for automated runs

## Local Testing with Docker

Before deploying to Google Cloud, you can test the application locally using Docker:

1. **Build the Docker image**:
   ```bash
   docker build -t cloud-case-study-scraper .
   ```

2. **Run the container locally**:
   ```bash
   docker run -p 8080:8080 cloud-case-study-scraper
   ```

3. **Or use Docker Compose**:
   ```bash
   docker-compose up
   ```

4. **Access the API**:
   - Open http://localhost:8080/docs in your browser to see the Swagger UI
   - Test the endpoints using the Swagger UI or curl commands

## Google Cloud Deployment

### Prerequisites

1. **Google Cloud Project**:
   - Create or select a Google Cloud project
   - Enable the following APIs:
     - Cloud Run API
     - Cloud Build API
     - Cloud Scheduler API
     - Cloud Storage API

2. **Service Account**:
   - Create a service account with the following roles:
     - Cloud Run Admin
     - Cloud Storage Admin
     - Cloud Scheduler Admin
     - Service Account User

3. **Storage Bucket**:
   - Create a Cloud Storage bucket for data persistence
   - Note the bucket name for configuration

### Deployment Options

#### Option 1: Manual Deployment

1. **Build and push the Docker image**:
   ```bash
   docker build -t gcr.io/[PROJECT_ID]/cloud-case-study-scraper .
   docker push gcr.io/[PROJECT_ID]/cloud-case-study-scraper
   ```

2. **Deploy to Cloud Run**:
   ```bash
   gcloud run deploy cloud-case-study-scraper \
     --image gcr.io/[PROJECT_ID]/cloud-case-study-scraper \
     --platform managed \
     --region us-central1 \
     --memory 2Gi \
     --cpu 1 \
     --timeout 3600 \
     --concurrency 1 \
     --set-env-vars="STORAGE_BUCKET=[YOUR_BUCKET_NAME],AUTO_START_SCHEDULER=true" \
     --service-account=[YOUR_SERVICE_ACCOUNT_EMAIL] \
     --no-allow-unauthenticated
   ```

3. **Create Cloud Scheduler jobs**:
   ```bash
   # For AWS scraping (daily at 2 AM)
   gcloud scheduler jobs create http aws-case-study-scraper \
     --schedule="0 2 * * *" \
     --uri="https://[YOUR_SERVICE_URL]/scrape?provider=aws" \
     --http-method=POST \
     --oidc-service-account-email=[YOUR_SERVICE_ACCOUNT_EMAIL] \
     --oidc-token-audience=[YOUR_SERVICE_URL]

   # For GCP scraping (daily at 3 AM)
   gcloud scheduler jobs create http gcp-case-study-scraper \
     --schedule="0 3 * * *" \
     --uri="https://[YOUR_SERVICE_URL]/scrape?provider=gcp" \
     --http-method=POST \
     --oidc-service-account-email=[YOUR_SERVICE_ACCOUNT_EMAIL] \
     --oidc-token-audience=[YOUR_SERVICE_URL]

   # For embedding (daily at 4 AM)
   gcloud scheduler jobs create http case-study-embedder \
     --schedule="0 4 * * *" \
     --uri="https://[YOUR_SERVICE_URL]/embed" \
     --http-method=POST \
     --oidc-service-account-email=[YOUR_SERVICE_ACCOUNT_EMAIL] \
     --oidc-token-audience=[YOUR_SERVICE_URL]
   ```

#### Option 2: Automated Deployment with Cloud Build

1. **Connect your GitHub repository to Cloud Build**:
   - Go to Cloud Build > Triggers
   - Connect your GitHub repository
   - Create a new trigger that uses the cloudbuild.yaml file

2. **Set up substitution variables**:
   - `_STORAGE_BUCKET`: Your Cloud Storage bucket name
   - `_SERVICE_ACCOUNT`: Your service account email
   - `_REGION_TAG`: The region where your service is deployed (default: us-central1)

3. **Push to GitHub to trigger deployment**:
   - Any push to your main branch will trigger the build and deployment process

## API Endpoints

The deployed service exposes the following endpoints:

- `GET /`: Root endpoint, returns API status
- `GET /health`: Health check endpoint
- `POST /scrape`: Trigger scraping process
  - Query parameters:
    - `provider`: Cloud provider (aws or gcp)
    - `max_pages`: Maximum number of pages to scrape (default: 5)
- `POST /embed`: Trigger embedding process
  - Query parameters:
    - `provider`: Cloud provider (aws or gcp)
    - `batch_size`: Number of case studies to embed (default: 10)
- `GET /sync`: Manually trigger a sync with cloud storage
- `GET /schedule`: Start the scheduled jobs

## Making Code Changes

When you make changes to your code:

1. **Push to GitHub**:
   - If you've set up Cloud Build, pushing to your main branch will automatically trigger a new build and deployment

2. **Manual update**:
   - If you're not using Cloud Build, rebuild and push your Docker image, then update your Cloud Run service

## Monitoring and Troubleshooting

- **View logs**:
  - Go to Cloud Run > cloud-case-study-scraper > Logs
  - Filter logs by severity or search for specific terms

- **Check Cloud Storage**:
  - Verify that files are being synced to your Cloud Storage bucket

- **Test endpoints manually**:
  - Use curl or a tool like Postman to test the API endpoints

## Cost Optimization

- Cloud Run only charges for the time your service is actually running
- Consider adjusting the memory and CPU allocation based on your needs
- Monitor your usage and adjust resources accordingly 