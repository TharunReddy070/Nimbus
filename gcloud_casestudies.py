import asyncio
import os
import sys
import logging
import pandas as pd
import PyPDF2
import io
import shutil
from pathlib import Path
from playwright.async_api import async_playwright
from db_manager import DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('gcp_processor.log')
    ]
)
logger = logging.getLogger('gcp_casestudies')

async def process_case_studies(provider="gcp"):
    """Process GCP case studies, save PDFs and add to database"""
    # Create directory structure
    base_dir = Path(provider.upper())
    pdf_dir = base_dir / 'PDF'
    txt_dir = base_dir / 'TXT'
    backup_dir = Path('backup') / provider
    
    for directory in [base_dir, pdf_dir, txt_dir, backup_dir]:
        directory.mkdir(exist_ok=True, parents=True)
    
    # Initialize database manager
    db = DatabaseManager()
    
    # Read links from CSV - only from backup directory
    csv_path = backup_dir / f"{provider}_case_study_links.csv"
    
    if not csv_path.exists():
        logger.error(f"No CSV file found at {csv_path}")
        return 0
    
    # Read the CSV
    df = pd.read_csv(csv_path)
    
    # Ensure required columns exist
    if 'is_processed' not in df.columns:
        df['is_processed'] = False
        logger.info("Added is_processed column to CSV")
    
    if 'page_number' not in df.columns:
        df['page_number'] = 1  # Default to page 1 for existing entries
        logger.info("Added page_number column to CSV")
    
    # Save any column updates back to the CSV
    df.to_csv(csv_path, index=False)
    logger.info(f"Updated CSV file with required columns")
    
    # Determine last ID
    last_id = 0
    
    # Check existing PDF files
    if pdf_dir.exists():
        pdf_files = list(pdf_dir.glob('*.pdf'))
        if pdf_files:
            pdf_ids = []
            for pdf_file in pdf_files:
                try:
                    # Extract ID from filename (like "123.pdf")
                    file_id = int(pdf_file.stem)
                    pdf_ids.append(file_id)
                except ValueError:
                    # If filename doesn't convert to int, skip it
                    continue
            
            if pdf_ids:
                last_id = max(pdf_ids)
                logger.info(f"Last ID from PDF files: {last_id}")
    
    # Check database for last ID
    db_last_id = db.get_last_id(provider)
    if db_last_id and db_last_id > last_id:
        last_id = db_last_id
        logger.info(f"Last ID from database: {last_id}")
    
    # Get unprocessed links
    unprocessed_df = df[~df['is_processed']]
    
    if unprocessed_df.empty:
        logger.info("No unprocessed case studies found")
        return 0
    
    # Sort by page number to process in order
    unprocessed_df = unprocessed_df.sort_values(by='page_number')
    
    links = unprocessed_df['link'].tolist()
    page_numbers = unprocessed_df['page_number'].tolist()
    
    logger.info(f"Processing {len(links)} unprocessed GCP case studies")
    
    processed_count = 0
    error_count = 0
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        for i, (link, page_number) in enumerate(zip(links, page_numbers)):
            current_link_row = df[df['link'] == link].index[0]
            
            try:
                # Check if link already exists in database
                if db.link_exists(provider, link):
                    logger.info(f"Skipping existing link ({i+1}/{len(links)}) from page {page_number}: {link}")
                    # Mark as processed in the DataFrame
                    df.loc[current_link_row, 'is_processed'] = True
                    continue
                
                logger.info(f"Processing ({i+1}/{len(links)}) from page {page_number}: {link}")
                
                # Navigate to the page
                await page.goto(link, wait_until='networkidle')
                await page.wait_for_load_state('networkidle')
                
                # Wait for content to load
                await page.wait_for_timeout(2000)
                
                # Generate new ID and filenames
                new_id = last_id + 1
                pdf_path = pdf_dir / f"{new_id}.pdf"
                txt_path = txt_dir / f"{new_id}.txt"
                
                # Save page as PDF
                await page.pdf(path=str(pdf_path), format='A4')
                logger.info(f"Saved PDF: {pdf_path}")
                
                # Save link as .txt
                with open(txt_path, "w") as f:
                    f.write(link)
                logger.info(f"Saved link: {txt_path}")
                
                # Extract text content from PDF
                content = ""
                try:
                    with open(pdf_path, 'rb') as pdf_file:
                        pdf_reader = PyPDF2.PdfReader(pdf_file)
                        for page_num in range(len(pdf_reader.pages)):
                            content += pdf_reader.pages[page_num].extract_text() + "\n"
                    logger.info(f"Extracted {len(content)} characters of text from PDF")
                except Exception as e:
                    logger.error(f"Error extracting text from PDF: {str(e)}")
                    # If PDF extraction fails, get content from page
                    content = await page.content()
                    logger.info(f"Using HTML content instead: {len(content)} characters")
                
                # Add to database
                db.save_content(
                    id=new_id,
                    provider=provider,
                    link=link,
                    pdf_path=str(pdf_path.relative_to(Path('.'))),
                    txt_path=str(txt_path.relative_to(Path('.'))),
                    content=content,
                    is_embedded=0  # Set is_embedded to 0 initially
                )
                
                # Mark as processed in the DataFrame
                df.loc[current_link_row, 'is_processed'] = True
                
                # Update last_id
                last_id = new_id
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Error processing {link} from page {page_number}: {str(e)}")
                
                # Save a record with null values to maintain ID sequence
                error_message = str(e)
                db.save_error_record(
                    id=new_id,
                    provider=provider,
                    link=link,
                    error=error_message
                )
                logger.info(f"Saved error record with ID {new_id} for failed processing")
                
                # Mark as processed even if there was an error
                df.loc[current_link_row, 'is_processed'] = True
                
                # Update last_id since we used this ID for the error record
                last_id = new_id
                error_count += 1
                
                # Save the updated DataFrame after each error to ensure we don't retry failed links
                df.to_csv(csv_path, index=False)
                logger.info(f"Updated CSV after error (marked link as processed)")
                continue
        
        await browser.close()
    
    # Save updated DataFrame with is_processed flags
    df.to_csv(csv_path, index=False)
    logger.info(f"Updated CSV with processing status")
    
    logger.info(f"Successfully processed {processed_count} GCP case studies, encountered errors on {error_count}")
    return processed_count

def display_case_studies(provider=None, limit=None):
    """Display case studies from the database"""
    db = DatabaseManager()
    case_studies = db.get_case_studies(provider=provider, limit=limit)
    
    if not case_studies:
        print(f"No case studies found{' for ' + provider if provider else ''}")
        return
    
    print(f"\nDisplaying {len(case_studies)} case studies{' for ' + provider if provider else ''}:")
    print("-" * 100)
    
    for cs in case_studies:
        print(f"ID: {cs['id']}")
        print(f"Provider: {cs['provider']}")
        print(f"Link: {cs['link']}")
        
        # Check if this is an error record
        if cs['is_embedded'] == -1:
            print(f"Status: ERROR - Processing Failed")
            print(f"Error: {cs['content'].replace('ERROR: ', '')}")
        else:
            print(f"PDF: {cs['pdf_path']}")
            print(f"Created: {cs['created_at']}")
            print(f"Embedded: {'Yes' if cs['is_embedded'] else 'No'}")
        
        print("-" * 100)

async def main():
    """Main function to process case studies"""
    try:
        count = await process_case_studies()
        return count
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        return 0

if __name__ == "__main__":
    # Check for display flag
    if len(sys.argv) > 1 and sys.argv[1] == "--display":
        provider = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] not in ["--limit", "--errors"] else None
        
        # Check for errors flag
        show_errors_only = "--errors" in sys.argv
        
        limit = None
        if "--limit" in sys.argv:
            limit_index = sys.argv.index("--limit")
            if limit_index + 1 < len(sys.argv):
                try:
                    limit = int(sys.argv[limit_index + 1])
                except ValueError:
                    print(f"Invalid limit value: {sys.argv[limit_index + 1]}")
        
        if show_errors_only:
            # Display only error records
            db = DatabaseManager()
            error_records = db.get_error_records(provider=provider, limit=limit)
            
            if not error_records:
                print(f"No error records found{' for ' + provider if provider else ''}")
                sys.exit(0)
            
            print(f"\nDisplaying {len(error_records)} error records{' for ' + provider if provider else ''}:")
            print("-" * 100)
            
            for er in error_records:
                print(f"ID: {er['id']}")
                print(f"Provider: {er['provider']}")
                print(f"Link: {er['link']}")
                print(f"Status: ERROR - Processing Failed")
                print(f"Error: {er['content'].replace('ERROR: ', '')}")
                print(f"Created: {er['created_at']}")
                print("-" * 100)
        else:
            # Display all case studies
            display_case_studies(provider, limit)
    else:
        # Process case studies
        asyncio.run(main())
