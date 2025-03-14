#!/usr/bin/env python3
import os
import sys
import json
import asyncio
import logging
import aiohttp
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

async def rewrite_aws_content():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # --- Configuration Constants ---
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

    # Get current directory and set paths
    current_dir = Path(__file__).parent
    INPUT_DIR = current_dir / "aws_pdf"
    OUTPUT_DIR = current_dir / "aws_json"

    BATCH_SIZE = 10         # Number of parallel requests (adjust to 5 if needed)
    RETRY_LIMIT = 3         # Maximum number of retries for each file

    # Ensure the output directory exists
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # --- JSON Schema for Response ---
    json_schema = {
        "name": "case_study",
        "schema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Noise free exact same content as the initial case study."
                },
                "metadata": {
                    "type": "object",
                    "description": "Metadata describing the case study.",
                    "properties": {
                        "link": {
                            "type": "string",
                            "description": "The URL link to the case study."
                        },
                        "company_name": {
                            "type": "string",
                            "description": "The name of the company being discussed in the case study."
                        },
                        "aws_services_used": {
                            "type": "array",
                            "description": "List of AWS services used by the company.",
                            "items": {
                                "type": "string"
                            }
                        },
                        "outcomes": {
                            "type": "array",
                            "description": "List of outcomes resulting from using the cloud services.",
                            "items": {
                                "type": "string"
                            }
                        },
                        "region": {
                            "type": "string",
                            "description": "The region where the company operates."
                        },
                        "year": {
                            "type": "number",
                            "description": "The year the case study refers to."
                        },
                        "industry": {
                            "type": "string",
                            "description": "The industry to which the company belongs."
                        },
                        "summary": {
                            "type": "string",
                            "description": "A brief summary of the case study."
                        }
                    },
                    "required": [
                        "link",
                        "company_name",
                        "aws_services_used",
                        "outcomes",
                        "region",
                        "year",
                        "industry",
                        "summary"
                    ],
                    "additionalProperties": False
                }
            },
            "required": [
                "content",
                "metadata"
            ],
            "additionalProperties": False
        },
        "strict": True
    }

    # --- Prompt Template ---
    prompt_template = """
    ### Task
    You are an advanced language model specialized in structured content extraction and refinement. Your task is to take the provided case study content and produce a **noise-free, well-structured version** while retaining **every single detail**. 

    ### Instructions
    1. **No missing information**: Ensure that every fact, statistic, quote, technical detail etc is included. Without losing any information. 
    2. **No extra content**: Do not add any new insights, interpretations, or filler words.
    3. **Consistent formatting**: Use markdown-style structuring, such as headings (`##`), subheadings (`###`), bullet points (`-`), and percentages (`%`).
    4. **Exact content**: Do not change the content of the case study. Just remove the noise.
    ### Input (Raw Scraped Content)
    {scraped_case_study}

    ### Expected Output
    Return a clean, structured version of the above content following the given guidelines along with the metadata.
    """

    # --- Request Headers ---
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }

    # Global list to collect skipped file numbers
    skipped_files = []

    async def process_file(file_number, semaphore, session, prompt_template):
        """
        Process a single file: read its content, build the prompt and call the OpenAI API,
        and then save the output JSON. If any error occurs or if the file is missing,
        log the issue and add the file number to the skipped_files list.
        """
        file_path = os.path.join(INPUT_DIR, f"{file_number}.txt")
        if not os.path.exists(file_path):
            logging.info(f"File {file_path} does not exist. Skipping.")
            skipped_files.append(file_number)
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                file_content = f.read()
        except Exception as e:
            logging.error(f"Error reading file {file_path}: {e}")
            skipped_files.append(file_number)
            return

        # Fill in the template
        prompt = prompt_template.format(scraped_case_study=file_content)

        # Prepare the API payload
        payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "response_format": {
                "type": "json_schema",
                "json_schema": json_schema
            }
        }

        # Retry loop for API calls
        for attempt in range(1, RETRY_LIMIT + 1):
            async with semaphore:
                try:
                    async with session.post(OPENAI_API_URL, headers=headers, json=payload) as response:
                        if response.status != 200:
                            logging.error(f"API error for file {file_number}. HTTP Status: {response.status}. Attempt: {attempt}")
                            await asyncio.sleep(2)
                            continue

                        resp_json = await response.json()

                        # Save output
                        output_file_path = os.path.join(OUTPUT_DIR, f"{file_number}.json")
                        with open(output_file_path, "w", encoding="utf-8") as outfile:
                            json.dump(resp_json, outfile, indent=4)
                        logging.info(f"Successfully processed file {file_number}.txt")
                        break  # Exit loop on successful processing

                except Exception as e:
                    logging.error(f"Exception for file {file_number} on attempt {attempt}: {e}")
                    await asyncio.sleep(2)
        else:
            logging.error(f"Failed to process file {file_number} after {RETRY_LIMIT} attempts.")
            skipped_files.append(file_number)

    async def process_all_files():
        """Process all txt files in the INPUT_DIR."""
        # Get list of all txt files and extract their numbers
        txt_files = [f for f in os.listdir(INPUT_DIR) if f.endswith('.txt')]
        file_numbers = [int(f.split('.')[0]) for f in txt_files]
        
        if not file_numbers:
            logging.warning("No txt files found in aws_pdf directory")
            return
            
        logging.info(f"Found {len(file_numbers)} files to process")
        
        semaphore = asyncio.Semaphore(BATCH_SIZE)
        tasks = []
        async with aiohttp.ClientSession() as session:
            for file_num in file_numbers:
                tasks.append(process_file(file_num, semaphore, session, prompt_template))
            await asyncio.gather(*tasks)

    # Process all files instead of requiring start/end
    await process_all_files()

    if skipped_files:
        logging.info("Skipped file numbers: %s", skipped_files)
    else:
        logging.info("All files processed successfully.")

if __name__ == "__main__":
    asyncio.run(rewrite_aws_content())
