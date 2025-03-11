import asyncio
import os
import pandas as pd
import PyPDF2
import io
from pathlib import Path
from playwright.async_api import async_playwright
from db_manager import DatabaseManager

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
        return 0
    
    # Read the CSV
    df = pd.read_csv(csv_path)
    
    # Ensure required columns exist
    if 'is_processed' not in df.columns:
        df['is_processed'] = False
    
    # Get unprocessed links
    unprocessed_df = df[df['is_processed'] == False]
    
    if unprocessed_df.empty:
        return 0
    
    # Determine last ID
    last_id = 0
    
    # Check existing PDF files
    if pdf_dir.exists():
        pdf_files = list(pdf_dir.glob('*.pdf'))
        if pdf_files:
            pdf_ids = []
            for pdf_file in pdf_files:
                try:
                    file_id = int(pdf_file.stem)
                    pdf_ids.append(file_id)
                except ValueError:
                    continue
            if pdf_ids:
                last_id = max(pdf_ids)
    
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
                pdf_button = await page.query_selector("a[href$='.pdf']")
                
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
                            # Save error record to database
                            db.save_error_record(
                                id=current_id,
                                provider=provider,
                                link=link,
                                error=str(e)
                            )
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

async def main(provider="gcp"):
    """Main function to run the GCP case study processor"""
    try:
        last_id = await process_case_studies(provider=provider)
        return last_id
    except Exception as e:
        print(f"Error processing {provider} case studies: {str(e)}")
        return 0

if __name__ == "__main__":
    import sys
    
    # Default to GCP if no provider specified
    provider = sys.argv[1] if len(sys.argv) > 1 else "gcp"
    
    asyncio.run(process_case_studies(provider=provider))
