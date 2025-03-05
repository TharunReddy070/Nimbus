from playwright.async_api import async_playwright
import asyncio
import pandas as pd
import os
from pathlib import Path
from db_manager import DatabaseManager 
import PyPDF2
import io

async def process_case_studies(provider="aws"):
    """Process case studies from CSV, save PDFs, and store in database"""
    # Create directories if they don't exist
    base_dir = Path(f'{provider.upper()}')
    base_dir.mkdir(exist_ok=True)
    
    pdf_dir = base_dir / 'PDF'
    txt_dir = base_dir / 'TXT'
    backup_dir = Path('backup') / provider
    
    for dir_path in [pdf_dir, txt_dir, backup_dir]:
        dir_path.mkdir(exist_ok=True, parents=True)
    
    # Load links from CSV
    csv_path = backup_dir / f'{provider}_case_study_links.csv'
    if not csv_path.exists():
        print(f"No links CSV found for {provider}!")
        return
    
    df = pd.read_csv(csv_path)
    
    # Add is_processed column if it doesn't exist
    if 'is_processed' not in df.columns:
        df['is_processed'] = False
    
    db = DatabaseManager()
    
    # Determine last ID by checking:
    # 1. Existing PDF files
    # 2. Database (if implemented in DatabaseManager)
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
                    continue
            
            if pdf_ids:
                last_id = max(pdf_ids)
                print(f"Found existing PDFs for {provider}, last ID: {last_id}")
    
    # Check database for last ID
    try:
        db_last_id = db.get_last_id(provider)
        if db_last_id and db_last_id > last_id:
            last_id = db_last_id
            print(f"Found entries in database for {provider}, last ID: {last_id}")
    except Exception as e:
        print(f"Error retrieving last ID from database: {str(e)}")
    
    # Filter to only unprocessed links
    unprocessed_df = df[df['is_processed'] == False]
    print(f"Found {len(unprocessed_df)} unprocessed links for {provider}")
    
    if unprocessed_df.empty:
        print(f"No new links to process for {provider}")
        return
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        next_id = last_id + 1  # Start with the next available ID
        
        for idx, row in unprocessed_df.iterrows():
            try:
                link = row['link']
                
                # Generate unique ID
                idnumber = next_id
                next_id += 1  # Increment for next link
                
                print(f"Processing {provider} case study {idnumber}: {link}")
                
                # Save PDF and link files
                pdf_path = pdf_dir / f"{idnumber}.pdf"
                txt_path = txt_dir / f"{idnumber}.txt"
                
                # Navigate to page and save PDF
                await page.goto(link, wait_until='networkidle')
                await page.wait_for_load_state('networkidle')
                await page.wait_for_timeout(2000)
                await page.pdf(path=str(pdf_path), format='A4')
                
                # Save link to txt file
                with open(txt_path, "w") as f:
                    f.write(link)
                
                # Extract text from PDF
                text_content = ""
                with open(pdf_path, 'rb') as pdf_file:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    for page_num in range(len(pdf_reader.pages)):
                        text_content += pdf_reader.pages[page_num].extract_text()
                
                # Store in database
                db.save_content(idnumber, provider, link, str(pdf_path), str(txt_path), text_content)
                
                print(f"Processed and stored {provider} case study {idnumber}")
                
            except Exception as e:
                print(f"Error processing link {link}: {str(e)}")
                
                # Save a record with error information to maintain ID sequence
                error_message = str(e)
                db.save_error_record(
                    id=idnumber,
                    provider=provider,
                    link=link,
                    error=error_message
                )
                print(f"Saved error record with ID {idnumber} for failed processing")
            finally:
                # Mark as processed regardless of success or failure
                df.at[idx, 'is_processed'] = True
        
        await browser.close()
    
    # Save updated CSV with processed flags
    df.to_csv(csv_path, index=False)
    print(f"Updated CSV with processed status for {provider}")

def display_case_studies(provider=None, limit=None):
    """Display case studies with newest first, optionally filtered by provider"""
    db = DatabaseManager()
    case_studies = db.get_case_studies(provider, limit)
    
    if not case_studies:
        provider_msg = f"for {provider}" if provider else ""
        print(f"No case studies found in database {provider_msg}.")
        return
    
    print(f"\n{'ID':<5}{'Provider':<10}{'Status':<15}{'Created At':<25}{'Link':<50}")
    print("-" * 105)
    
    for study in case_studies:
        id = study['id']
        provider = study['provider']
        link = study['link']
        is_embedded = study['is_embedded']
        created_at = study['created_at']
        
        # Determine status based on is_embedded value
        if is_embedded == -1:
            status = "ERROR"
        elif is_embedded == 1:
            status = "Embedded"
        else:
            status = "Not Embedded"
        
        # Truncate link if too long
        display_link = link[:47] + "..." if len(link) > 50 else link
        
        print(f"{id:<5}{provider:<10}{status:<15}{created_at:<25}{display_link:<50}")
        
        # If this is an error record, show the error message
        if is_embedded == -1:
            error_msg = study['content'].replace('ERROR: ', '')
            print(f"  Error: {error_msg}")
    
    print("-" * 105)
    
    provider_msg = f"for {provider}" if provider else ""
    print(f"\nTotal: {len(case_studies)} case studies {provider_msg}")
    db.close()

async def main():
    """Main function to run the AWS case study processor"""
    try:
        await process_case_studies()
        return True
    except Exception as e:
        print(f"Error processing AWS case studies: {str(e)}")
        return False

if __name__ == "__main__":
    import sys
    
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