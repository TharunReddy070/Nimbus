import time
from playwright.async_api import async_playwright
import asyncio
import pandas as pd
import os
from pathlib import Path

async def save_pages_as_pdf_and_links():
    # Get current directory (scrapping)
    current_dir = Path(__file__).parent
    
    # Create PDF directory in scrapping folder
    pdf_dir = current_dir / 'aws_pdf'
    pdf_dir.mkdir(exist_ok=True)
    
    # Read links from CSV in scrapping directory
    csv_path = current_dir / '1.csv'
    df = pd.read_csv(csv_path)
    links = df['link'].tolist()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)  # Set to headless mode
        page = await browser.new_page()
        
        # for index, link in enumerate(links[:2], 1):
        for index, link in enumerate(links, 1):
            try:
                print(f"Processing {index}/{len(links)}: {link}")
                
                # Navigate to the page
                await page.goto(link, wait_until='networkidle')
                await page.wait_for_load_state('networkidle')

                # Check for and close the popup button if it exists
                close_button = await page.query_selector("button[aria-label='Close']")
                if close_button:
                    await close_button.click()
                    print("Closed the popup button.")

                time.sleep(10)

                # Wait for content to load
                await page.wait_for_timeout(2000)
                
                # Save page as PDF
                pdf_path = pdf_dir / f"{index}.pdf"
                await page.pdf(path=str(pdf_path), format='A4')
                print(f"Saved PDF: {pdf_path}")
                
                # Save link as .txt
                txt_path = pdf_dir / f"{index}.txt"
                txt_path.write_text(link)
                print(f"Saved link: {txt_path}")

                # Update is_scraped value to True in the DataFrame
                df.loc[df['link'] == link, 'is_scraped'] = True
                
            except Exception as e:
                print(f"Error processing {link}: {str(e)}")
                continue
        
        # Save the updated DataFrame back to CSV
        df.to_csv(csv_path, index=False)
        print(f"Updated scraping status in {csv_path}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(save_pages_as_pdf_and_links())