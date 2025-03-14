import time
from playwright.async_api import async_playwright
import asyncio
import pandas as pd
import os
from pathlib import Path

async def scrape_aws_case_studies():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto('https://aws.amazon.com/solutions/case-studies/')

        time.sleep(10)
        await page.wait_for_load_state('networkidle')

        # Check for and close the popup button if it exists
        close_button = await page.query_selector("button[aria-label='Close']")
        if close_button:
            await close_button.click()
            print("Closed the popup button.")

        all_links = []
        max_pages = 5
        current_page = 1
        
        while current_page <= max_pages:
            # Extract links
            links = await page.eval_on_selector_all(
                "//div[contains(@class, 'm-card-img')]/a",
                "elements => elements.map(element => element.href)"
            )
            all_links.extend(links)
            print(f"Page {current_page}: Found {len(links)} links")
            
            # Navigate to next page
            next_button = await page.query_selector("//a[contains(@class, 'm-icon-angle-right m-active')]")
            if next_button and current_page < max_pages:
                await next_button.click()
                await page.wait_for_load_state('networkidle')
                await page.wait_for_timeout(2000)
                current_page += 1
            else:
                break
        
        # Save links to CSV with additional columns
        df = pd.DataFrame(all_links, columns=['link'])
        df['is_embedded'] = False
        df['is_scraped'] = False
        
        # Save to the correct path in scrapping directory
        current_dir = Path(__file__).parent
        output_path = current_dir / '1.csv'
        df.to_csv(output_path, index=False)
        print(f"Saved {len(all_links)} links to {output_path}")
        
        await browser.close()
        return str(output_path)

if __name__ == "__main__":
    asyncio.run(scrape_aws_case_studies())