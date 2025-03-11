import schedule
import time
import asyncio
import logging
import argparse
import sys
from datetime import datetime
from AWS_links import main as aws_links_main
from AWS_casestudies import main as aws_casestudies_main
from gcloud_links import main as gcp_links_main
from gcloud_casestudies import main as gcp_casestudies_main
from azure_links import main as azure_links_main
from azure_casestudies import main as azure_casestudies_main
from embedding_example import process_embeddings
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scheduler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("cloud_case_study_scheduler")

# Define supported providers
PROVIDERS = ["aws", "gcp", "azure"]

async def scrape_pipeline(provider="aws", max_pages=None):
    """Run the complete scraping pipeline for a specific provider"""
    # Set default max_pages based on provider if not specified
    if max_pages is None:
        # For AWS: max_pages is the number of pages to scrape
        # For GCP: max_pages is the maximum page number to reach
        # For Azure: max_pages is the maximum page number to reach
        if provider.lower() == "aws":
            max_pages = 3
        elif provider.lower() == "gcp":
            max_pages = 2
        else:  # azure
            max_pages = 3
        
    logger.info(f"Starting {provider} scraping pipeline at {datetime.now()}")
    
    # Step 1: Extract new links to CSV
    if provider.lower() == "aws":
        logger.info(f"Step 1: Extracting new {provider} case study links (max pages: {max_pages})...")
    else:
        logger.info(f"Step 1: Extracting new {provider} case study links (max page: {max_pages})...")
    
    # Set environment variable for scheduler
    os.environ['FROM_SCHEDULER'] = 'true'
    
    new_links = 0
    if provider.lower() == "aws":
        new_links = await aws_links_main(max_pages)
    elif provider.lower() == "gcp":
        new_links = await gcp_links_main(max_pages)
    elif provider.lower() == "azure":
        new_links = await azure_links_main(1, max_pages, "Azure")  # start_page=1, max_pages=max_pages, search_query="Azure"
    else:
        logger.error(f"Unsupported provider: {provider}")
        return
    
    # Step 2: Process case studies (always run this step)
    logger.info(f"Step 2: Processing {provider} case studies...")
    if provider.lower() == "aws":
        await aws_casestudies_main()
    elif provider.lower() == "gcp":
        await gcp_casestudies_main()
    elif provider.lower() == "azure":
        await azure_casestudies_main()
    
    # Reset environment variable
    os.environ['FROM_SCHEDULER'] = 'false'
    
    logger.info(f"Completed {provider} scraping pipeline at {datetime.now()}")

def run_scrape_pipeline(provider="aws", max_pages=None):
    """Helper function to run the async pipeline for a specific provider"""
    asyncio.run(scrape_pipeline(provider, max_pages))

def run_embedding_pipeline(provider=None, batch_size=10):
    """Run the embedding pipeline for all or a specific provider"""
    logger.info(f"Starting embedding pipeline at {datetime.now()}")
    
    providers_to_process = [provider] if provider else PROVIDERS
    
    for p in providers_to_process:
        if p not in PROVIDERS:
            logger.error(f"Unsupported provider: {p}")
            continue
            
        logger.info(f"Processing embeddings for {p} case studies...")
        process_embeddings(provider=p, batch_size=batch_size)
    
    logger.info(f"Completed embedding pipeline at {datetime.now()}")

def start_scheduler():
    """Start the scheduler with predefined jobs"""
    logger.info("Starting cloud case study scheduler")
    
    # Schedule AWS scraping daily at 2:00 AM
    schedule.every().day.at("02:00").do(
        run_scrape_pipeline, 
        provider="aws",
        max_pages=3
    )
    logger.info("Scheduled AWS scraping: Daily at 02:00 AM (3 pages)")
    
    # Schedule GCP scraping daily at 3:00 AM
    schedule.every().day.at("03:00").do(
        run_scrape_pipeline, 
        provider="gcp",
        max_pages=2
    )
    logger.info("Scheduled GCP scraping: Daily at 03:00 AM (up to page 2)")
    
    # Schedule Azure scraping daily at 4:00 AM
    schedule.every().day.at("04:00").do(
        run_scrape_pipeline, 
        provider="azure",
        max_pages=3
    )
    logger.info("Scheduled Azure scraping: Daily at 04:00 AM (up to page 3)")
    
    # TEMPORARILY DISABLED: Schedule embedding daily at 5:00 AM
    # This job is commented out until the embedding logic is fully implemented
    # Uncomment this section when embedding functionality is ready
    # schedule.every().day.at("05:00").do(run_embedding_pipeline)
    # logger.info("Scheduled embedding: Daily at 05:00 AM")
    
    logger.info("Scheduler is running. Press Ctrl+C to exit.")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")

def run_immediate_scrape(provider=None, max_pages=None):
    """Run immediate scraping for all or a specific provider"""
    providers_to_process = [provider] if provider else PROVIDERS
    
    for p in providers_to_process:
        if p not in PROVIDERS:
            logger.error(f"Unsupported provider: {p}")
            continue
        
        # Set default max_pages based on provider if not specified
        if max_pages is None:
            provider_max_pages = 3 if p.lower() == "aws" else 2
        else:
            provider_max_pages = max_pages
            
        if p.lower() == "aws":
            logger.info(f"Running immediate scraping for {p} (max pages: {provider_max_pages})...")
        else:
            logger.info(f"Running immediate scraping for {p} (max page: {provider_max_pages})...")
            
        run_scrape_pipeline(provider=p, max_pages=provider_max_pages)

def run_immediate_embed(provider=None, batch_size=None):
    """Run immediate embedding for all or a specific provider"""
    batch_size = batch_size or 10  # Default to 10 case studies per batch
    
    logger.info(f"Running immediate embedding{' for ' + provider if provider else ''} (batch size: {batch_size})...")
    run_embedding_pipeline(provider=provider, batch_size=batch_size)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cloud Case Study Scheduler")
    
    # Define mutually exclusive group for main actions
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument("--service", action="store_true", help="Run as a service with scheduled jobs")
    action_group.add_argument("--scrape", action="store_true", help="Run immediate scraping")
    action_group.add_argument("--embed", action="store_true", help="Run immediate embedding")
    
    # Optional arguments
    parser.add_argument("--provider", choices=PROVIDERS, help="Specify provider (aws, gcp, or azure)")
    parser.add_argument("--max-pages", type=int, help="Maximum pages to scrape")
    parser.add_argument("--batch-size", type=int, help="Batch size for embedding")
    
    # Parse arguments
    args = parser.parse_args()
    
    if args.service:
        start_scheduler()
    elif args.scrape:
        run_immediate_scrape(provider=args.provider, max_pages=args.max_pages)
    elif args.embed:
        run_immediate_embed(provider=args.provider, batch_size=args.batch_size)
