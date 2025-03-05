# Cloud Case Study Scraper - Deployment Guide

This guide provides detailed instructions for deploying the Cloud Case Study Scraper using Docker and Google Cloud Run.

## Important Note

The embedding functionality is temporarily disabled until the embedding logic is fully implemented. The scheduler job for embedding at 4:00 AM has been commented out in both the scheduler.py file and the cloudbuild.yaml file. When you're ready to implement embedding, you'll need to uncomment these sections.

## Local Deployment with Docker

### Prerequisites
- Docker and Docker Compose installed on your machine
- Git repository cloned to your local machine

### Steps

1. **Create required directories**:
   ```bash
   mkdir -p AWS/PDF AWS/TXT GCP/PDF GCP/TXT backup/aws backup/gcp database logs
   ```

2. **Create empty log files**:
   ```bash
   touch logs/aws_scraper.log logs/gcp_scraper.log logs/scheduler.log
   ```

3. **Build and run with Docker Compose**:
   ```bash
   docker-compose up --build
   ```

4. **Access the API**:
   - Open http://localhost:8080/docs in your browser to see the Swagger UI
   - Test the endpoints using the Swagger UI or curl commands

5. **View logs**:
   - Logs are stored in the `logs` directory
   - You can view them in real-time with:
     ```bash
     tail -f logs/aws_scraper.log
     tail -f logs/gcp_scraper.log
     tail -f logs/scheduler.log
     ```

## Google Cloud Run Deployment

### Prerequisites
1. **Google Cloud Account and Project**:
   - Create a Google Cloud account if you don't have one
   - Create a new project or select an existing one

2. **Set Up Billing Account** (CRITICAL):
   - Go to Billing in the Google Cloud Console
   - Create a new billing account if you don't have one
   - Link your billing account to your project
   - Note: You cannot enable most Google Cloud services without an active billing account
   - New users are eligible for $300 in free credits for 90 days

3. **Enable Required APIs**:
   - After setting up billing, enable the following APIs:
     - Cloud Run API
     - Cloud Build API
     - Cloud Scheduler API
     - Cloud Storage API

4. **Install Google Cloud SDK**:
   - Follow the instructions at https://cloud.google.com/sdk/docs/install

5. **Create a Service Account**:
   - Go to IAM & Admin > Service Accounts
   - Create a new service account with the following roles:
     - Cloud Run Admin
     - Cloud Storage Admin
     - Cloud Scheduler Admin
     - Service Account User
   - Download the JSON key file

6. **Create a Cloud Storage Bucket**:
   - Go to Cloud Storage > Buckets
   - Create a new bucket for storing your data
   - Note the bucket name for configuration

### Deployment Options

#### Option 1: Manual Deployment

1. **Authenticate with Google Cloud**:
   ```bash
   gcloud auth login
   gcloud config set project [YOUR_PROJECT_ID]
   ```

2. **Build and push the Docker image**:
   ```bash
   docker build -t gcr.io/[YOUR_PROJECT_ID]/cloud-case-study-scraper .
   docker push gcr.io/[YOUR_PROJECT_ID]/cloud-case-study-scraper
   ```

3. **Deploy to Cloud Run**:
   ```bash
   gcloud run deploy cloud-case-study-scraper \
     --image gcr.io/[YOUR_PROJECT_ID]/cloud-case-study-scraper \
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

4. **Create Cloud Scheduler jobs**:
   ```bash
   # For AWS scraping (daily at 2 AM)
   gcloud scheduler jobs create http aws-case-study-scraper \
     --schedule="0 2 * * *" \
     --uri="https://[YOUR_SERVICE_URL]/scrape?provider=aws&max-pages=3" \
     --http-method=POST \
     --oidc-service-account-email=[YOUR_SERVICE_ACCOUNT_EMAIL] \
     --oidc-token-audience=[YOUR_SERVICE_URL]

   # For GCP scraping (daily at 3 AM)
   gcloud scheduler jobs create http gcp-case-study-scraper \
     --schedule="0 3 * * *" \
     --uri="https://[YOUR_SERVICE_URL]/scrape?provider=gcp&max-pages=2" \
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

#### Option 2: Automated Deployment with GitHub and Cloud Build

1. **Push your code to GitHub**:
   ```bash
   git add .
   git commit -m "Prepare for cloud deployment"
   git push origin main
   ```

2. **Connect your GitHub repository to Cloud Build**:
   - Go to Cloud Build > Triggers
   - Connect your GitHub repository
   - Create a new trigger that uses the cloudbuild.yaml file

3. **Set up substitution variables**:
   - `_STORAGE_BUCKET`: Your Cloud Storage bucket name
   - `_SERVICE_ACCOUNT`: Your service account email
   - `_REGION_TAG`: The region where your service is deployed (default: us-central1)

4. **Push changes to GitHub to trigger deployment**:
   - Any push to your main branch will trigger the build and deployment process

## Monitoring and Troubleshooting

### Viewing Logs in Google Cloud

1. **Cloud Run Logs**:
   - Go to Cloud Run > cloud-case-study-scraper > Logs
   - Filter logs by severity or search for specific terms

2. **Cloud Storage**:
   - Verify that files are being synced to your Cloud Storage bucket
   - Check the bucket contents periodically

3. **Cloud Scheduler**:
   - Go to Cloud Scheduler to view the status of your scheduled jobs
   - Check the execution history for any failures

### Common Issues and Solutions

1. **Scraper fails to extract links**:
   - Check if the website structure has changed
   - Update the selectors in the scraper code
   - Verify that Playwright is working correctly

2. **PDF download fails**:
   - Check if the PDF URL format has changed
   - Verify that the storage directories exist and are writable
   - Check for network connectivity issues

3. **Scheduler not running**:
   - Verify that the `AUTO_START_SCHEDULER` environment variable is set to `true`
   - Check the scheduler logs for any errors
   - Restart the service if necessary

## Maintenance

### Updating the Application

1. **Make code changes**:
   - Update the code as needed
   - Test locally using Docker

2. **Deploy updates**:
   - If using GitHub and Cloud Build, push changes to GitHub
   - If using manual deployment, rebuild and push the Docker image, then update the Cloud Run service

### Backing Up Data

1. **Database Backup**:
   - The SQLite database is automatically synced to Cloud Storage
   - You can download it from the bucket for manual backups

2. **PDF and Text Files**:
   - All PDF and text files are stored in Cloud Storage
   - They can be downloaded for backup purposes

## Security Considerations

1. **Service Account Permissions**:
   - Use the principle of least privilege
   - Only grant necessary permissions to the service account

2. **API Access**:
   - The Cloud Run service is configured with `--no-allow-unauthenticated`
   - Only authenticated requests with proper credentials can access the API

3. **Secrets Management**:
   - Store sensitive information like API keys in Secret Manager
   - Mount secrets as environment variables in the Cloud Run service

## Cost Optimization

1. **Cloud Run**:
   - Cloud Run only charges for the time your service is actually running
   - Consider adjusting the memory and CPU allocation based on your needs

2. **Cloud Storage**:
   - Use the appropriate storage class for your needs
   - Consider lifecycle policies to archive or delete old data

3. **Cloud Scheduler**:
   - Cloud Scheduler has a free tier for a limited number of jobs
   - Consolidate jobs if possible to stay within the free tier 