import schedule
import time
import asyncio
import argparse
import sys
from datetime import datetime
from AWS_links import main as aws_links_main
from AWS_casestudies import main as aws_casestudies_main
from gcloud_links import main as gcp_links_main
from gcloud_casestudies import main as gcp_casestudies_main
from embedding_example import process_embeddings
import os

# Define supported providers
PROVIDERS = ["aws", "gcp"]

async def scrape_pipeline(provider="aws", max_pages=None):
    """Run the complete scraping pipeline for a specific provider"""
    # Set default max_pages based on provider if not specified
    if max_pages is None:
        # For AWS: max_pages is the number of pages to scrape
        # For GCP: max_pages is the maximum page number to reach
        if provider.lower() == "aws":
            max_pages = 3
        else:  # gcp
            max_pages = 2
    
    # Step 1: Extract new links to CSV
    if provider.lower() == "aws":
        # Set environment variable to indicate we're running from scheduler
        os.environ['FROM_SCHEDULER'] = 'true'
        new_links = await aws_links_main(max_pages)
    elif provider.lower() == "gcp":
        # Set environment variable to indicate we're running from scheduler
        os.environ['FROM_SCHEDULER'] = 'true'
        new_links = await gcp_links_main(max_pages)
    else:
        return 0
    
    # Step 2: Process case studies (if new links were found)
    if new_links > 0:
        if provider.lower() == "aws":
            await aws_casestudies_main(provider)
        elif provider.lower() == "gcp":
            await gcp_casestudies_main(provider)
    
    # Step 3: Generate embeddings for new case studies
    await process_embeddings(provider)
    
    # Clear environment variable
    if 'FROM_SCHEDULER' in os.environ:
        del os.environ['FROM_SCHEDULER']
    
    return new_links

def run_scrape_pipeline(provider="aws", max_pages=None):
    """Run the scrape pipeline synchronously (for scheduling)"""
    return asyncio.run(scrape_pipeline(provider, max_pages))

def schedule_jobs(interval_hours=24, run_immediately=False):
    """Schedule scraping jobs to run at specified intervals"""
    # Schedule AWS scraping
    schedule.every(interval_hours).hours.do(run_scrape_pipeline, provider="aws")
    
    # Schedule GCP scraping
    schedule.every(interval_hours).hours.do(run_scrape_pipeline, provider="gcp")
    
    # Run immediately if requested
    if run_immediately:
        print(f"Running initial scrape for all providers...")
        for provider in PROVIDERS:
            run_scrape_pipeline(provider)
    
    # Keep the scheduler running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

def main():
    """Main function to parse arguments and run the scheduler"""
    parser = argparse.ArgumentParser(description="Cloud Case Study Scraper Scheduler")
    
    # Add subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Schedule command
    schedule_parser = subparsers.add_parser("schedule", help="Schedule scraping jobs")
    schedule_parser.add_argument("--interval", type=int, default=24, help="Interval in hours between scrapes (default: 24)")
    schedule_parser.add_argument("--run-now", action="store_true", help="Run scraping immediately after starting scheduler")
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Run scraping pipeline once")
    run_parser.add_argument("provider", choices=PROVIDERS, help="Provider to scrape")
    run_parser.add_argument("--max-pages", type=int, help="Maximum number of pages to scrape")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Execute command
    if args.command == "schedule":
        print(f"Starting scheduler with {args.interval} hour interval...")
        schedule_jobs(args.interval, args.run_now)
    elif args.command == "run":
        print(f"Running scrape pipeline for {args.provider}...")
        run_scrape_pipeline(args.provider, args.max_pages)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
