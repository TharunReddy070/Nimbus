from playwright.async_api import async_playwright
import asyncio
import pandas as pd
from pathlib import Path

async def scrape_aws_case_studies(start_page=2, max_pages=3, provider="aws"):
    """Extract AWS case study links and store in CSV
    
    Args:
        start_page: The page number to start scraping from (default: 2)
        max_pages: The maximum page number to scrape up to (inclusive) (default: 3)
        provider: The cloud provider name (default: aws)
    """
    # Create backup directory if it doesn't exist
    backup_dir = Path('backup') / provider
    backup_dir.mkdir(exist_ok=True, parents=True)
    
    # Load existing links from CSV if it exists
    csv_path = backup_dir / f'{provider}_case_study_links.csv'
    existing_links = set()
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        existing_links = set(df['link'].tolist())
    
    new_links = []
    current_page = 1
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto('https://aws.amazon.com/solutions/case-studies/')
        await page.wait_for_load_state('networkidle')
        
        # Navigate to start_page
        while current_page < start_page:
            next_button = await page.query_selector("//a[contains(@class, 'm-icon-angle-right m-active')]")
            if next_button:
                await next_button.click()
                await page.wait_for_load_state('networkidle')
                await page.wait_for_timeout(2000)
                current_page += 1
            else:
                break
        
        # Scrape from start_page to max_pages (inclusive)
        while current_page <= max_pages:
            # Extract links using existing selector
            links = await page.eval_on_selector_all(
                "//div[contains(@class, 'm-card-img')]/a",
                "elements => elements.map(element => element.href)"
            )
            
            # Filter out existing links
            new_page_links = [(current_page, link) for link in links if link not in existing_links]
            if new_page_links:
                new_links.extend(new_page_links)
            
            # Navigate to next page if we haven't reached max_pages
            if current_page < max_pages:
                next_button = await page.query_selector("//a[contains(@class, 'm-icon-angle-right m-active')]")
                if next_button:
                    await next_button.click()
                    await page.wait_for_load_state('networkidle')
                    await page.wait_for_timeout(2000)
                    current_page += 1
                else:
                    break
            else:
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
        else:
            new_df.to_csv(csv_path, index=False)
    
    return new_links

# Function to scrape Google Cloud case studies (placeholder for future implementation)
async def scrape_gcp_case_studies(start_page=1, max_pages=2, provider="gcp"):
    """Placeholder for Google Cloud case study scraping"""
    return []

async def main(max_pages=3):
    """Main function to run the AWS scraper with specified parameters"""
    try:
        # Start from page 1 when called from scheduler
        links = await scrape_aws_case_studies(start_page=1, max_pages=max_pages)
        return len(links)
    except Exception:
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