import os
import csv
import asyncio
import argparse
from playwright.async_api import async_playwright

async def scrape_azure_links(start_page=1, max_pages=3, output_file="azure_links.csv", append_mode=True):
    """
    Scrape Azure case study links from Microsoft's website using async Playwright.
    
    Args:
        start_page (int): Page number to start scraping from
        max_pages (int): Maximum number of pages to scrape
        output_file (str): CSV file to save the links
        append_mode (bool): If True, append to existing CSV; if False, overwrite
    
    Returns:
        int: Number of new unique links scraped
        int: Last page successfully scraped
    """
    # Track all links to avoid duplicates
    all_links = set()
    
    # Load existing links if in append mode
    if append_mode and os.path.exists(output_file):
        try:
            with open(output_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                for row in reader:
                    if len(row) >= 2:  # Ensure row has enough columns
                        all_links.add(row[1])  # Add link to set
            print(f"Loaded {len(all_links)} existing links from {output_file}")
        except Exception as e:
            print(f"Error loading existing links: {e}")
    
    # Create CSV file with header if it doesn't exist or if not in append mode
    if not os.path.exists(output_file) or not append_mode:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['page_number', 'link', 'is_embedded'])
        if not append_mode:
            print(f"Created new file: {output_file}")
    
    # Initialize Playwright
    playwright = None
    browser = None
    
    try:
        playwright = await async_playwright().start()
        # Launch browser with increased timeout
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        page = await context.new_page()
        
        # Set longer timeouts for navigation
        page.set_default_timeout(60000)  # 60 seconds
        
        # Navigate to the Azure customers page
        await page.goto('https://www.microsoft.com/en-us/customers/search?filters=product%3Aazure', wait_until='networkidle')
        
        # Wait for the initial load of cards
        await page.wait_for_selector("//*[contains(@class, 'layout layout--cols-3')]/div")
        
        # If start_page > 1, navigate to that page
        current_page = 1
        try:
            while current_page < start_page:
                next_button = page.locator("//button[@aria-label='Next']")
                
                # Check if next button exists and is enabled
                if await next_button.count() == 0 or not await next_button.is_enabled():
                    print(f"Cannot navigate to page {start_page}. Last available page is {current_page}.")
                    return 0, current_page
                
                await next_button.click()
                await page.wait_for_selector("//*[contains(@class, 'layout layout--cols-3')]/div", state='visible')
                await page.wait_for_timeout(3000)  # Increased wait time for content to load
                current_page += 1
        except Exception as e:
            print(f"Error navigating to start page: {e}")
            return 0, current_page
        
        # Scrape links from start_page to max_pages
        total_links = 0
        new_links = 0
        last_page_scraped = start_page - 1  # Initialize to the page before we start
        
        for i in range(start_page, start_page + max_pages):
            try:
                # Update the last page we've successfully scraped
                last_page_scraped = i
                
                # Wait for the cards to be visible
                await page.wait_for_selector("//*[contains(@class, 'layout layout--cols-3')]/div", state='visible')
                await page.wait_for_timeout(3000)  # Ensure content is fully loaded
                
                # Get all case study links
                story_links = await page.locator("//a[contains(@aria-label, 'Read the story')]").all()
                
                # Process each link
                page_links = 0
                page_new_links = 0
                for link in story_links:
                    href = await link.get_attribute('href')
                    
                    if href:
                        # Remove any duplicate domain if present
                        clean_href = href if href.startswith('https://www.microsoft.com') else f"https://www.microsoft.com{href}"
                        
                        # Count all links on this page
                        page_links += 1
                        
                        # Skip if we've already seen this link
                        if clean_href in all_links:
                            continue
                        
                        # Add to our set of all links
                        all_links.add(clean_href)
                        
                        # Append to CSV file
                        with open(output_file, 'a', newline='', encoding='utf-8') as f:
                            writer = csv.writer(f)
                            writer.writerow([i, clean_href, 'false'])
                        
                        page_new_links += 1
                        new_links += 1
                
                print(f"Page {i}: Found {page_links} links, saved {page_new_links} new unique links")
                total_links += page_links
                
                # Click next page if not on the last iteration
                if i < start_page + max_pages - 1:
                    next_button = page.locator("//button[@aria-label='Next']")
                    
                    # Check if next button exists and is enabled
                    if await next_button.count() == 0 or not await next_button.is_enabled():
                        print(f"Reached the last page at page {i}. Stopping.")
                        break
                    
                    await next_button.click()
                    
                    # Wait for the new page content to load
                    await page.wait_for_selector("//*[contains(@class, 'layout layout--cols-3')]/div", state='visible')
                    
                    # Add a longer delay to ensure content is fully loaded
                    await page.wait_for_timeout(5000)
            except Exception as e:
                print(f"Error on page {i}: {e}")
                break
                
        print(f"Completed! Found {total_links} total links, added {new_links} new unique links to {output_file}")
        print(f"Total unique links in {output_file}: {len(all_links)}")
        return new_links, last_page_scraped
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return 0, start_page - 1
    
    finally:
        # Make sure to close the browser and playwright
        if browser:
            await browser.close()
        if playwright:
            await playwright.stop()

async def main_async():
    """Async main function to run the Azure links scraper."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Scrape Azure case study links')
    parser.add_argument('--start-page', type=int, default=1, help='Page number to start scraping from')
    parser.add_argument('--max-pages', type=int, default=190, help='Maximum number of pages to scrape per run')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing CSV instead of appending')
    parser.add_argument('--runs', type=int, default=1, help='Number of runs to perform')
    args = parser.parse_args()
    
    max_pages = args.max_pages
    output_file = "azure_links.csv"  # Hardcoded output file name
    
    # First run determines append mode based on overwrite flag
    append_mode = not args.overwrite
    
    for run in range(1, args.runs + 1):
        print(f"\n--- Starting run {run}/{args.runs} ---")
        
        # Always start from page 1 for each run
        start_page = 1
        
        # Run the scraper
        new_links, last_page = await scrape_azure_links(
            start_page, 
            max_pages, 
            output_file, 
            append_mode
        )
        
        # Force append mode to True for subsequent runs
        append_mode = True
        
        print(f"--- Completed run {run}/{args.runs} ---")
        print(f"Last page scraped: {last_page}")
        print(f"Total new unique links in this run: {new_links}")
        
        if new_links == 0:
            print("No new links found in this run. Stopping additional runs.")
            break

def main():
    """Main function to run the async Azure links scraper."""
    asyncio.run(main_async())

if __name__ == "__main__":
    main() 