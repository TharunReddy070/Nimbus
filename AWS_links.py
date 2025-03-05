from playwright.async_api import async_playwright
import asyncio
import pandas as pd
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('aws_scraper.log')
    ]
)
logger = logging.getLogger('aws_links')

async def scrape_aws_case_studies(start_page=2, max_pages=3, provider="aws"):
    """Extract AWS case study links and store in CSV (not directly in database)
    
    Args:
        start_page: The page number to start scraping from (default: 2)
        max_pages: The maximum page number to scrape up to (inclusive) (default: 3)
        provider: The cloud provider name (default: aws)
    """
    logger.info(f"Starting AWS case study scraping from page {start_page} to page {max_pages}")
    
    # Create backup directory if it doesn't exist
    backup_dir = Path('backup') / provider
    backup_dir.mkdir(exist_ok=True, parents=True)
    
    # Load existing links from CSV if it exists
    csv_path = backup_dir / f'{provider}_case_study_links.csv'
    existing_links = set()
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        existing_links = set(df['link'].tolist())
        logger.info(f"Found {len(existing_links)} existing links in CSV")
    
    new_links = []
    current_page = 1
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto('https://aws.amazon.com/solutions/case-studies/')
        await page.wait_for_load_state('networkidle')
        logger.info(f"Loaded initial AWS case studies page")
        
        # Navigate to start_page
        while current_page < start_page:
            next_button = await page.query_selector("//a[contains(@class, 'm-icon-angle-right m-active')]")
            if next_button:
                await next_button.click()
                await page.wait_for_load_state('networkidle')
                await page.wait_for_timeout(2000)
                current_page += 1
                logger.info(f"Navigated to page {current_page}")
            else:
                logger.warning(f"Could not navigate to start page {start_page}, stopped at page {current_page}")
                break
        
        # Scrape from start_page to max_pages (inclusive)
        while current_page <= max_pages:
            # Extract links using existing selector
            links = await page.eval_on_selector_all(
                "//div[contains(@class, 'm-card-img')]/a",
                "elements => elements.map(element => element.href)"
            )
            
            logger.info(f"Found {len(links)} total links on page {current_page}")
            
            # Filter out existing links
            new_page_links = [(current_page, link) for link in links if link not in existing_links]
            if new_page_links:
                new_links.extend(new_page_links)
                logger.info(f"Page {current_page}: Found {len(new_page_links)} new links")
            else:
                logger.info(f"Page {current_page}: No new links found")
            
            # Navigate to next page if we haven't reached max_pages
            if current_page < max_pages:
                next_button = await page.query_selector("//a[contains(@class, 'm-icon-angle-right m-active')]")
                if next_button:
                    await next_button.click()
                    await page.wait_for_load_state('networkidle')
                    await page.wait_for_timeout(2000)
                    current_page += 1
                    logger.info(f"Navigated to page {current_page}")
                else:
                    logger.info("No more pages available")
                    break
            else:
                logger.info(f"Reached maximum page number ({max_pages})")
                break
        
        await browser.close()
    
    # Save new links to CSV
    if new_links:
        new_df = pd.DataFrame(new_links, columns=['page_number', 'link'])
        # Add is_processed column set to False for all new links
        new_df['is_processed'] = False
        
        if csv_path.exists():
            # Append new links to existing CSV
            existing_df = pd.read_csv(csv_path)
            combined_df = pd.concat([new_df, existing_df], ignore_index=True)
            combined_df.to_csv(csv_path, index=False)
            logger.info(f"Added {len(new_links)} new links to existing CSV file ({csv_path})")
        else:
            new_df.to_csv(csv_path, index=False)
            logger.info(f"Created new CSV file with {len(new_links)} links ({csv_path})")
    else:
        logger.info("No new links found")
    
    return new_links

# Function to scrape Google Cloud case studies (placeholder for future implementation)
async def scrape_gcp_case_studies(start_page=1, max_pages=2, provider="gcp"):
    """Placeholder for Google Cloud case study scraping"""
    print("Google Cloud case study scraping not yet implemented")
    return []

async def main(max_pages=3):
    """Main function to run the AWS scraper with specified parameters"""
    try:
        # Start from page 1 when called from scheduler
        links = await scrape_aws_case_studies(start_page=1, max_pages=max_pages)
        return len(links)
    except Exception as e:
        logger.error(f"Error scraping AWS case studies: {str(e)}")
        return 0

if __name__ == "__main__":
    import sys
    
    # Default to AWS if no provider specified
    provider = sys.argv[1] if len(sys.argv) > 1 else "aws"
    
    if provider.lower() == "aws":
        asyncio.run(scrape_aws_case_studies(provider=provider))
    elif provider.lower() in ["gcp", "google"]:
        asyncio.run(scrape_gcp_case_studies(provider="gcp"))
    else:
        print(f"Unknown provider: {provider}")
        print("Supported providers: aws, gcp")