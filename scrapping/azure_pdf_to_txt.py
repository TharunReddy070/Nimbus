#!/usr/bin/env python3
import os
import sys
from pathlib import Path
import PyPDF2
import asyncio
from concurrent.futures import ThreadPoolExecutor

def process_pdf(pdf_path):
    """Extract text from a PDF file."""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
    except Exception as e:
        print(f"Error processing PDF {pdf_path}: {e}")
        return None

async def append_pdf_content():
    """Append PDF content to existing text files in the AZURE directory."""
    # Setup paths - using parent of scrapping directory
    current_dir = Path(__file__).parent.parent  # Go up one level from scrapping
    azure_dir = current_dir / "AZURE"  # AZURE directory in root

    if not azure_dir.exists():
        print(f"AZURE directory not found at {azure_dir}")
        return

    # Get list of all PDF files
    pdf_files = sorted([f for f in azure_dir.glob("*.pdf")], key=lambda x: int(x.stem))
    
    if not pdf_files:
        print("No PDF files found in AZURE directory")
        return

    total_files = len(pdf_files)
    print(f"Found {total_files} PDF files to process")
    
    # Process files using a thread pool
    with ThreadPoolExecutor() as executor:
        for pdf_file in pdf_files:
            txt_file = pdf_file.with_suffix('.txt')
            
            # Skip if text file doesn't exist
            if not txt_file.exists():
                print(f"Text file {txt_file.name} does not exist. Skipping.")
                continue

            print(f"Processing {pdf_file.name}")
            
            try:
                # Read existing content
                with open(txt_file, 'r', encoding='utf-8') as f:
                    existing_content = f.read().strip()

                # Extract text from PDF
                pdf_text = await asyncio.get_event_loop().run_in_executor(executor, process_pdf, pdf_file)
                
                if pdf_text:
                    try:
                        # Append PDF text to file with two blank lines after existing content
                        with open(txt_file, 'w', encoding='utf-8') as f:
                            f.write(existing_content)
                            f.write("\n\n")  # Add two blank lines
                            f.write(pdf_text)
                        print(f"Successfully appended content to {txt_file.name}")
                    except Exception as e:
                        print(f"Error writing to {txt_file}: {e}")
                else:
                    print(f"Failed to extract text from {pdf_file.name}")
            except Exception as e:
                print(f"Error processing {pdf_file.name}: {e}")

def main():
    """Main entry point."""
    print("Starting PDF content appending process")
    
    try:
        asyncio.run(append_pdf_content())
        print("PDF content appending completed")
    except Exception as e:
        print(f"An error occurred during processing: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 