from fastapi import FastAPI, BackgroundTasks, Query, Depends
import uvicorn
import asyncio
import subprocess
import os
from typing import Optional
from pydantic import BaseModel
from datetime import datetime
import logging

# Import the scraping and embedding functions
from AWS_links import main as aws_links_main
from AWS_casestudies import main as aws_casestudies_main
from gcloud_links import main as gcp_links_main
from gcloud_casestudies import main as gcp_casestudies_main
from embedding_example import process_embeddings
from cloud_storage import CloudStorage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("api.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("cloud_case_study_api")

app = FastAPI(
    title="Cloud Case Study Scraper API",
    description="API for scraping and processing cloud provider case studies",
    version="1.0.0"
)

# Define supported providers
PROVIDERS = ["aws", "gcp"]

# Initialize cloud storage
storage = CloudStorage()

# Dependency to sync from cloud before request
async def get_storage():
    storage.sync_from_cloud()
    return storage

class StatusResponse(BaseModel):
    status: str
    message: str
    timestamp: str

@app.get("/", response_model=StatusResponse)
async def root():
    """Root endpoint, returns API status"""
    return {
        "status": "online",
        "message": "Cloud Case Study Scraper API is running",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health", response_model=StatusResponse)
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "API is healthy and ready to process requests",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/scrape", response_model=StatusResponse)
async def scrape(
    background_tasks: BackgroundTasks,
    provider: Optional[str] = Query(None, description="Cloud provider (aws or gcp)"),
    max_pages: Optional[int] = Query(5, description="Maximum number of pages to scrape"),
    storage: CloudStorage = Depends(get_storage)
):
    """
    Trigger scraping process for cloud case studies
    
    - If provider is specified, only scrape that provider
    - If provider is not specified, scrape all supported providers
    - max_pages controls how many pages to scrape (default: 5)
    """
    providers_to_scrape = [provider.lower()] if provider else PROVIDERS
    
    # Validate provider
    if provider and provider.lower() not in PROVIDERS:
        return {
            "status": "error",
            "message": f"Unsupported provider: {provider}. Supported providers: {', '.join(PROVIDERS)}",
            "timestamp": datetime.now().isoformat()
        }
    
    background_tasks.add_task(run_scrape_task, providers_to_scrape, max_pages, storage)
    
    return {
        "status": "accepted",
        "message": f"Started scraping for providers: {', '.join(providers_to_scrape)} (max pages: {max_pages})",
        "timestamp": datetime.now().isoformat()
    }

async def run_scrape_task(providers, max_pages, storage):
    """Background task to run scraping for specified providers"""
    for provider in providers:
        try:
            logger.info(f"Starting scraping for {provider} (max pages: {max_pages})")
            
            # Step 1: Extract links
            if provider == "aws":
                link_count = await aws_links_main(max_pages)
            elif provider == "gcp":
                link_count = await gcp_links_main(max_pages)
            
            logger.info(f"Found {link_count} links for {provider}")
            
            # Step 2: Process case studies
            if provider == "aws":
                await aws_casestudies_main()
            elif provider == "gcp":
                await gcp_casestudies_main()
            
            logger.info(f"Completed scraping for {provider}")
            
        except Exception as e:
            logger.error(f"Error scraping {provider}: {str(e)}")
    
    # Sync to cloud storage after processing
    try:
        logger.info("Syncing to cloud storage")
        storage.sync_to_cloud()
        logger.info("Sync to cloud storage completed")
    except Exception as e:
        logger.error(f"Error syncing to cloud: {str(e)}")

@app.post("/embed", response_model=StatusResponse)
async def embed(
    background_tasks: BackgroundTasks,
    provider: Optional[str] = Query(None, description="Cloud provider (aws or gcp)"),
    batch_size: Optional[int] = Query(10, description="Number of case studies to embed"),
    storage: CloudStorage = Depends(get_storage)
):
    """
    Trigger embedding process for cloud case studies
    
    - If provider is specified, only embed that provider's case studies
    - If provider is not specified, embed all supported providers
    - batch_size controls how many case studies to embed (default: 10)
    """
    # Validate provider
    if provider and provider.lower() not in PROVIDERS:
        return {
            "status": "error",
            "message": f"Unsupported provider: {provider}. Supported providers: {', '.join(PROVIDERS)}",
            "timestamp": datetime.now().isoformat()
        }
    
    providers_to_embed = [provider.lower()] if provider else PROVIDERS
    background_tasks.add_task(run_embed_task, providers_to_embed, batch_size, storage)
    
    return {
        "status": "accepted",
        "message": f"Started embedding for providers: {', '.join(providers_to_embed)} (batch size: {batch_size})",
        "timestamp": datetime.now().isoformat()
    }

def run_embed_task(providers, batch_size, storage):
    """Background task to run embedding for specified providers"""
    for provider in providers:
        try:
            logger.info(f"Starting embedding for {provider} (batch size: {batch_size})")
            process_embeddings(provider=provider, batch_size=batch_size)
            logger.info(f"Completed embedding for {provider}")
        except Exception as e:
            logger.error(f"Error embedding {provider}: {str(e)}")
    
    # Sync to cloud storage after processing
    try:
        logger.info("Syncing to cloud storage")
        storage.sync_to_cloud()
        logger.info("Sync to cloud storage completed")
    except Exception as e:
        logger.error(f"Error syncing to cloud: {str(e)}")

@app.get("/sync", response_model=StatusResponse)
async def sync_storage(background_tasks: BackgroundTasks):
    """Manually trigger a sync with cloud storage"""
    background_tasks.add_task(run_sync)
    
    return {
        "status": "accepted",
        "message": "Started cloud storage sync",
        "timestamp": datetime.now().isoformat()
    }

def run_sync():
    """Background task to sync with cloud storage"""
    try:
        logger.info("Starting sync from cloud")
        storage.sync_from_cloud()
        logger.info("Completed sync from cloud")
        
        logger.info("Starting sync to cloud")
        storage.sync_to_cloud()
        logger.info("Completed sync to cloud")
    except Exception as e:
        logger.error(f"Error during sync: {str(e)}")

@app.get("/schedule", response_model=StatusResponse)
async def start_scheduled_jobs():
    """Start the scheduled jobs"""
    try:
        # Start the scheduler in a separate process
        subprocess.Popen(["python", "scheduler.py", "--service"])
        
        return {
            "status": "success",
            "message": "Scheduler started successfully",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error starting scheduler: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to start scheduler: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

@app.on_event("startup")
async def startup_event():
    """Run on API startup"""
    # Sync from cloud storage on startup
    try:
        logger.info("Syncing from cloud storage on startup")
        storage.sync_from_cloud()
        logger.info("Initial cloud sync completed")
    except Exception as e:
        logger.error(f"Error during initial cloud sync: {str(e)}")
    
    # Optionally start the scheduler automatically if environment variable is set
    if os.environ.get("AUTO_START_SCHEDULER", "").lower() == "true":
        try:
            logger.info("Auto-starting scheduler")
            subprocess.Popen(["python", "scheduler.py", "--service"])
            logger.info("Scheduler auto-started")
        except Exception as e:
            logger.error(f"Error auto-starting scheduler: {str(e)}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=False) 