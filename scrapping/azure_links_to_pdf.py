import time
from playwright.async_api import async_playwright
import asyncio
import pandas as pd
import os
import sys
from pathlib import Path

def reset_scraping_status():
    """
    Reset the scraping status of all links in the CSV file to False.
    This allows reprocessing all links from the beginning.
    """
    csv_path = Path(__file__).parent / 'azure_links.csv'
    
    if not csv_path.exists():
        print(f"Error: {csv_path} does not exist. Please run azure_links.py first.")
        return False
    
    try:
        # Read the CSV file
        df = pd.read_csv(csv_path)
        
        # Add is_scraped column if it doesn't exist
        if 'is_scraped' not in df.columns:
            df['is_scraped'] = False
        else:
            # Set all is_scraped values to False
            df['is_scraped'] = False
        
        # Save the updated DataFrame back to CSV
        df.to_csv(csv_path, index=False)
        
        print(f"Successfully reset scraping status for all {len(df)} links in {csv_path}")
        print("All links are now marked as not scraped and will be processed in the next run.")
        return True
    
    except Exception as e:
        print(f"Error resetting scraping status: {str(e)}")
        return False

# Process a single link and save its content
async def process_link(browser, link, index, azure_dir, df, csv_path, semaphore):
    async with semaphore:  # Limit concurrent operations
        context = None
        try:
            print(f"Processing {index}: {link}")
            
            # Create a new page for each link
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
            page = await context.new_page()
            
            # Increase timeouts significantly
            page.set_default_timeout(60000)  # 60 seconds timeout
            
            # Navigate to the page with longer timeout
            await page.goto(link, wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_load_state('networkidle', timeout=60000)  # Increased timeout
            
            # Wait for main content to be visible
            await page.wait_for_selector("main", timeout=60000)
            
            # Remove popups and overlays using JavaScript
            await page.evaluate("""() => {
                // Remove common overlay elements
                const overlaySelectors = [
                    '.modal', '.overlay', '.popup', '.dialog',
                    '#onetrust-consent-sdk', '.cookie-banner',
                    '.cookie-consent', '[role="dialog"]',
                    '[aria-modal="true"]', '.modal-backdrop',
                    '.fade.show', '.modal.show'
                ];
                
                // Remove elements
                overlaySelectors.forEach(selector => {
                    document.querySelectorAll(selector).forEach(el => el.remove());
                });
                
                // Reset body styles
                document.body.style.overflow = 'auto';
                document.body.style.position = 'static';
                document.body.style.paddingRight = '0';
                document.body.classList.remove('modal-open');
                
                // Remove fixed/sticky elements
                document.querySelectorAll('*').forEach(el => {
                    const style = window.getComputedStyle(el);
                    if (style.position === 'fixed' || style.position === 'sticky') {
                        el.style.position = 'static';
                    }
                });
            }""")
            
            # Wait for changes to apply
            await page.wait_for_timeout(2000)
            
            # Try to close any remaining visible buttons
            popup_selectors = [
                "button[aria-label='Close']",
                "button.close-button",
                "[aria-label='Close dialog']",
                "[aria-label='Close modal']",
                "[aria-label='close']",
                ".modal-close",
                ".close-modal",
                "#onetrust-close-btn-container button",
                ".cookie-banner button",
                ".cookie-consent button"
            ]
            
            for selector in popup_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for element in elements:
                        if await element.is_visible():
                            await element.click()
                            await page.wait_for_timeout(1000)
                except Exception:
                    continue
            
            # Final cleanup using JavaScript
            await page.evaluate("""() => {
                // Ensure all modal-related elements are removed
                document.querySelectorAll('[class*="modal"]').forEach(el => el.remove());
                document.querySelectorAll('[class*="popup"]').forEach(el => el.remove());
                document.querySelectorAll('[class*="overlay"]').forEach(el => el.remove());
            }""")
            
            # Wait for page to stabilize
            await page.wait_for_timeout(2000)
            
            # Save page as PDF using the current index (preserving numbering sequence)
            pdf_path = azure_dir / f"{index}.pdf"
            await page.pdf(path=str(pdf_path), format='A4', scale=0.8, margin={
                'top': '20px',
                'right': '20px',
                'bottom': '20px',
                'left': '20px'
            })
            print(f"Saved PDF: {pdf_path}")
            
            # Save link as .txt with matching index
            txt_path = azure_dir / f"{index}.txt"
            with open(txt_path, "w") as f:
                f.write(link)
            print(f"Saved link: {txt_path}")

            # Update is_scraped value to True in the DataFrame and save
            df.loc[df['link'] == link, 'is_scraped'] = True
            df.to_csv(csv_path, index=False)
            
            # Clean up resources
            await context.close()
            
            return True, index
            
        except Exception as e:
            print(f"Error processing link #{index}: {link}")
            print(f"The error was: {str(e)}")
            print(f"Skipping PDF #{index} and continuing with next link...")
            
            # Clean up in case of error
            if context:
                try:
                    await context.close()
                except:
                    pass
                
            return False, index

async def save_pages_as_pdf_and_links():
    # Get current directory
    current_dir = Path(__file__).parent
    
    # Create AZURE directory if it doesn't exist
    azure_dir = current_dir / 'AZURE'
    azure_dir.mkdir(exist_ok=True)
    
    # Find the highest PDF number in the AZURE folder
    highest_number = 0
    for pdf_file in azure_dir.glob("*.pdf"):
        try:
            file_number = int(pdf_file.stem)  # Get the number from filename (without extension)
            highest_number = max(highest_number, file_number)
        except ValueError:
            # Skip files that don't have numeric names
            continue
    
    print(f"Found highest PDF number: {highest_number}")
    start_number = highest_number + 1
    print(f"Will start numbering from: {start_number}")
    
    # Read links from azure_links.csv
    csv_path = current_dir / 'azure_links.csv'
    
    # Check if the file exists
    if not csv_path.exists():
        print(f"Error: {csv_path} does not exist. Please run azure_links.py first.")
        return
    
    # Read the CSV file
    df = pd.read_csv(csv_path)
    
    # Add is_scraped column if it doesn't exist
    if 'is_scraped' not in df.columns:
        df['is_scraped'] = False
    
    # Get links that haven't been scraped yet
    links = df[~df['is_scraped']]['link'].tolist()
    
    if not links:
        print("All links have already been scraped!")
        return
    
    print(f"Found {len(links)} links to process")
    
    # Create a semaphore to limit concurrent connections - reduce to 3 for more stability
    max_concurrent = 3  # Process 3 links simultaneously (reduced from 5)
    semaphore = asyncio.Semaphore(max_concurrent)
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            # Create tasks for all links
            tasks = []
            for i, link in enumerate(links):
                # Calculate file number starting from the next available number
                file_number = start_number + i
                
                task = process_link(browser, link, file_number, azure_dir, df, csv_path, semaphore)
                tasks.append(task)
            
            # Process all links concurrently and gather results
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count successful and failed links
            successful_count = sum(1 for result in results if isinstance(result, tuple) and result[0])
            failed_count = len(links) - successful_count
            
            print(f"Updated scraping status in {csv_path}")
            print(f"Completed! Successfully processed: {successful_count}, Failed: {failed_count}")
            print(f"Total links processed: {len(links)}")
            print(f"PDF numbering: {start_number} to {start_number + len(links) - 1}")
            
            # Close the browser
            await browser.close()
    except Exception as e:
        print(f"An error occurred in the main processing loop: {str(e)}")
        print("The script will exit, but your progress has been saved in the CSV file.")

if __name__ == "__main__":
    # Check if the user wants to reset scraping status
    if len(sys.argv) > 1 and sys.argv[1] == "--reset":
        reset_scraping_status()
    else:
        # Run the normal scraping process
        asyncio.run(save_pages_as_pdf_and_links()) 