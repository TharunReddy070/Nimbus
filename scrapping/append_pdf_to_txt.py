import os
from PyPDF2 import PdfReader
from pathlib import Path

async def append_pdf_to_txt():
    # Get current directory and aws_pdf directory
    current_dir = Path(__file__).parent
    aws_dir = current_dir / "aws_pdf"
    
    if not aws_dir.exists():
        print(f"Directory {aws_dir} does not exist")
        return
    
    # Get all txt files
    txt_files = list(aws_dir.glob("*.txt"))
    
    for txt_file in txt_files:
        # Get corresponding PDF file
        pdf_file = txt_file.with_suffix('.pdf')
        
        if pdf_file.exists():
            try:
                print(f"Processing {txt_file.name} and {pdf_file.name}")
                
                # Read PDF content
                with open(pdf_file, "rb") as pdf_file_obj:
                    pdf_reader = PdfReader(pdf_file_obj)
                    pdf_text = ""
                    for page in pdf_reader.pages:
                        pdf_text += page.extract_text() + "\n"
                
                # Append PDF text to TXT file
                with open(txt_file, "a", encoding='utf-8') as txt_file_obj:
                    txt_file_obj.write("\n\n")  # Leave two lines
                    txt_file_obj.write(pdf_text)
                
                print(f"Successfully appended PDF content to {txt_file.name}")
                
            except Exception as e:
                print(f"Error processing {txt_file.name}: {str(e)}")
                continue
        else:
            print(f"No matching PDF found for {txt_file.name}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(append_pdf_to_txt())
