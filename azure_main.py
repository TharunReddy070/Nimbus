#!/usr/bin/env python3
import os
import sys
import asyncio
import logging
from pathlib import Path
from scrapping.azure_pdf_to_txt import append_azure_pdf_to_txt
from scrapping.azure_content_rewriting import rewrite_azure_content
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('azure_processing.log')
    ]
)

async def main():
    """
    Main function to orchestrate the Azure case study processing workflow.
    First converts PDFs to text, then processes the content.
    """
    try:
        # Get current directory
        current_dir = Path(__file__).parent
        azure_dir = current_dir / "AZURE"
        json_dir = current_dir / "azure_json"

        # Ensure directories exist
        azure_dir.mkdir(exist_ok=True)
        json_dir.mkdir(exist_ok=True)

        print("\n=== Step 1: Converting PDFs to Text ===")
        await append_azure_pdf_to_txt()
        
        print("\n=== Step 2: Processing Content ===")
        await rewrite_azure_content()
        
        print("\n=== Processing Complete ===")
        
        # Check results
        txt_files = list(azure_dir.glob("*.txt"))
        json_files = list(json_dir.glob("*.json"))
        
        print("\nProcessed files:")
        print(f"Text files in AZURE: {len(txt_files)}")
        print(f"JSON files created: {len(json_files)}")
        
        if len(txt_files) != len(json_files):
            print(f"\nWarning: Number of text files ({len(txt_files)}) does not match number of JSON files ({len(json_files)})")
            
            # Find missing JSON files
            txt_numbers = {int(f.stem) for f in txt_files}
            json_numbers = {int(f.stem) for f in json_files}
            missing = sorted(txt_numbers - json_numbers)
            if missing:
                print(f"Missing JSON files for numbers: {missing}")

    except Exception as e:
        logging.error(f"Error in main: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    print("Starting Azure Case Study Processing Pipeline")
    asyncio.run(main())