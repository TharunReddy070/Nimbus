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
                    # Skip files that don't have numeric names
                    continue
            if pdf_ids:
                last_id = max(pdf_ids)
    
    # Get unprocessed links
    unprocessed_df = df[df['is_processed'] == False]
    
    if unprocessed_df.empty:
        print(f"No unprocessed links found for {provider}!")
        return
    
    # Process each unprocessed link
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        for index, row in unprocessed_df.iterrows():
            link = row['link']
            
            # Generate next ID
            last_id += 1
            current_id = last_id
            
            # Define file paths
            pdf_file = pdf_dir / f"{current_id}.pdf"
            txt_file = txt_dir / f"{current_id}.txt"
            
            try:
                # Navigate to the case study page
                await page.goto(link, timeout=60000)
                await page.wait_for_load_state('networkidle', timeout=60000)
                
                # Check if PDF download button exists
                pdf_button = await page.query_selector("a.pdf-cta")
                
                if pdf_button:
                    # Get PDF URL
                    pdf_url = await pdf_button.get_attribute('href')
                    
                    if pdf_url:
                        # Download PDF
                        pdf_response = await page.context.request.get(pdf_url)
                        pdf_data = await pdf_response.body()
                        
                        # Save PDF to file
                        with open(pdf_file, 'wb') as f:
                            f.write(pdf_data)
                        
                        # Extract text from PDF
                        try:
                            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_data))
                            text = ""
                            for page_num in range(len(pdf_reader.pages)):
                                text += pdf_reader.pages[page_num].extract_text()
                            
                            # Save text to file
                            with open(txt_file, 'w', encoding='utf-8') as f:
                                f.write(text)
                            
                            # Save to database
                            db.save_content(
                                id=current_id,
                                provider=provider,
                                link=link,
                                pdf_path=str(pdf_file),
                                txt_path=str(txt_file),
                                content=text
                            )
                            
                            # Mark as processed in DataFrame
                            df.at[index, 'is_processed'] = True
                        except Exception as e:
                            print(f"Error processing PDF for {link}: {str(e)}")
                            # Save error record to database
                            db.save_error_record(
                                id=current_id,
                                provider=provider,
                                link=link,
                                error=str(e)
                            )
                    else:
                        print(f"No PDF URL found for {link}")
                else:
                    # Try to extract content directly from the page
                    content = await page.content()
                    
                    # Extract text from HTML content
                    text = await page.evaluate('''() => {
                        const article = document.querySelector('article');
                        return article ? article.innerText : document.body.innerText;
                    }''')
                    
                    # Save text to file
                    with open(txt_file, 'w', encoding='utf-8') as f:
                        f.write(text)
                    
                    # Save to database
                    db.save_content(
                        id=current_id,
                        provider=provider,
                        link=link,
                        pdf_path="",  # No PDF
                        txt_path=str(txt_file),
                        content=text
                    )
                    
                    # Mark as processed in DataFrame
                    df.at[index, 'is_processed'] = True
            except Exception as e:
                print(f"Error processing {link}: {str(e)}")
                # Save error record to database
                db.save_error_record(
                    id=current_id,
                    provider=provider,
                    link=link,
                    error=str(e)
                )
        
        await browser.close()
    
    # Save updated DataFrame to CSV
    df.to_csv(csv_path, index=False)
    
    return last_id

async def main(provider="aws"):
    """Main function to run the AWS case study processor"""
    try:
        last_id = await process_case_studies(provider=provider)
        return last_id
    except Exception as e:
        print(f"Error processing {provider} case studies: {str(e)}")
        return 0

if __name__ == "__main__":
    import sys
    
    # Default to AWS if no provider specified
    provider = sys.argv[1] if len(sys.argv) > 1 else "aws"
    
    asyncio.run(process_case_studies(provider=provider))