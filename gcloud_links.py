import asyncio
import os
import sys
import pandas as pd
from pathlib import Path
from playwright.async_api import async_playwright

async def scrape_case_studies(max_pages=2, provider="GCP", skip_count=18):
    """
    Scrape case study links from the GCP case studies page.
    
    Args:
        max_pages: Maximum page number to reach (default: 2, which means initial page + 1 'More' click)
        provider: Provider name for the CSV file (default: "GCP")
        skip_count: Number of initial links to skip (default: 18)
        
    Returns:
        Number of new links saved
    """
    # Create directory structure
    base_dir = Path(provider.upper())
    base_dir.mkdir(exist_ok=True)
    
    backup_dir = Path('backup') / provider.lower()
    backup_dir.mkdir(exist_ok=True, parents=True)
    
    # Output file path
    csv_file = backup_dir / f"{provider.lower()}_case_study_links.csv"
    
    # Check for existing links and load existing DataFrame
    existing_df = None
    existing_links = []
    
    if csv_file.exists():
        try:
            existing_df = pd.read_csv(csv_file)
            # Add is_processed column if it doesn't exist
            if 'is_processed' not in existing_df.columns:
                existing_df['is_processed'] = False
            
            # Add page_number column if it doesn't exist
            if 'page_number' not in existing_df.columns:
                existing_df['page_number'] = 1  # Default to page 1 for existing entries
            
            existing_links = existing_df['link'].tolist()
        except Exception:
            # Create a new DataFrame if there was an error
            existing_df = pd.DataFrame(columns=['link', 'page_number', 'is_processed'])
    else:
        # Create a new DataFrame if the file doesn't exist
        existing_df = pd.DataFrame(columns=['link', 'page_number', 'is_processed'])
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Navigate to the GCP case studies page
        await page.goto("https://cloud.google.com/customers?sr=IiUIARIhGh9DT1JQVVNfVFlQRV9DVVNUT01FUl9DQVNFX1NUVURZKAw6CBoECgJlbigB")
        await page.wait_for_load_state("networkidle")
        
        all_case_study_links = []
        current_page = 1  # Start with page 1 (initial load)

        # First, extract links from the initial page load
        links = await page.eval_on_selector_all(
            "//a[contains(@class, 'aOrzRd')]",
            "elements => elements.map(element => element.href)"
        )
        
        # Add initial links
        for link in links:
            all_case_study_links.append((current_page, link))  # Store page number with link

        # Click the "More" button until we reach max_pages
        while current_page < max_pages:
            # Click the "More" button
            more_button = await page.query_selector("button:has-text('More')")
            if more_button:
                await more_button.click()
                await page.wait_for_timeout(3000)  # Wait longer for the new content to load
                await page.wait_for_load_state('networkidle')  # Wait for network to be idle
                current_page += 1  # Increment page count
                
                # Extract new links after clicking "More"
                links = await page.eval_on_selector_all(
                    "//a[contains(@class, 'aOrzRd')]",
                    "elements => elements.map(element => element.href)"
                )
                
                # Add only new links while maintaining order
                for link in links:
                    if link not in [l for _, l in all_case_study_links]:
                        all_case_study_links.append((current_page, link))  # Store page number with link
            else:
                break

        # Process links, skipping the first 18
        if skip_count > 0:
            filtered_links = all_case_study_links[skip_count:]
        else:
            filtered_links = all_case_study_links

        # Filter out existing links
        new_links = [(page_num, link) for page_num, link in filtered_links if link not in existing_links]

        # Save new links to CSV
        if new_links:
            # Create new DataFrame for new links
            new_links_df = pd.DataFrame(new_links, columns=['page_number', 'link'])
            new_links_df['is_processed'] = False
            
            # If we have an existing DataFrame, concatenate with new links
            if existing_df is not None:
                combined_df = pd.concat([existing_df, new_links_df], ignore_index=True)
            else:
                combined_df = new_links_df
            
            # Save the combined DataFrame
            combined_df.to_csv(csv_file, index=False)
        else:
            # If we have an existing DataFrame but no new links, still save it to ensure columns are added
            if existing_df is not None:
                existing_df.to_csv(csv_file, index=False)

        await browser.close()
        
        return len(new_links)

async def main(max_pages=2):
    """
    Run the scraper.
    
    Args:
        max_pages: Maximum page number to reach (default: 2, which means initial page + 1 'More' click)
    """
    try:
        # Check if being called from scheduler
        from_scheduler = os.environ.get('FROM_SCHEDULER', 'false').lower() == 'true'
        
        # If called from scheduler, don't skip any links
        skip_count = 0 if from_scheduler else 18
        
        # Run the scraper
        num_links = await scrape_case_studies(max_pages=max_pages, provider="GCP", skip_count=skip_count)
        
        return num_links
        
    except Exception:
        return 0

if __name__ == "__main__":
    asyncio.run(main())
