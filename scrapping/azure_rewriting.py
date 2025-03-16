#!/usr/bin/env python3
import os
import sys
import json
import asyncio
import aiohttp
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

async def rewrite_azure_content():
    """
    Process Azure case studies using OpenAI to extract structured content and metadata.
    Processes all files in the AZURE directory.
    """
    # --- Configuration Constants ---
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        print("OPENAI_API_KEY not found in environment variables")
        return

    OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

    # Get current directory and set paths
    current_dir = Path(__file__).parent.parent  # Go up one level from scrapping
    INPUT_DIR = current_dir / "AZURE"  # AZURE directory in root
    OUTPUT_DIR = current_dir / "azure_json"  # azure_json directory in root

    BATCH_SIZE = 3          # Number of parallel requests
    RETRY_LIMIT = 3         # Maximum number of retries for each file

    # Ensure the output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

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
                        "azure_services_used": {
                            "type": "array",
                            "description": "List of Azure services used by the company.",
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
                        "azure_services_used",
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
    You are an advanced language model specialized in structured content extraction and refinement. Your task is to take the provided Azure case study content and produce a **noise-free, well-structured version** while retaining **every single detail**. 

    ### Instructions
    1. **No missing information**: Ensure that every fact, statistic, quote, technical detail etc is included. Without losing any information. 
    2. **No extra content**: Do not add any new insights, interpretations, or filler words.
    3. **Consistent formatting**: Use markdown-style structuring, such as headings (`##`), subheadings (`###`), bullet points (`-`), and percentages (`%`).
    4. **Exact content**: Do not change the content of the case study. Just remove the noise.

    ### Input (Raw Scraped Content)
    {case_study}

    ### Expected Output
    Return a clean, structured version of the above content following the given guidelines along with the metadata."""

    # --- Request Headers ---
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }

    # Global list to collect skipped file numbers
    skipped_files = []

    async def process_file(file_number, semaphore, session):
        """Process a single file and generate structured content."""
        file_path = os.path.join(INPUT_DIR, f"{file_number}.txt")
        if not os.path.exists(file_path):
            print(f"File {file_path} does not exist. Skipping.")
            skipped_files.append(file_number)
            return

        # Skip if output file already exists
        output_file_path = os.path.join(OUTPUT_DIR, f"{file_number}.json")
        if os.path.exists(output_file_path):
            print(f"Output file {output_file_path} already exists. Skipping.")
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                file_content = f.read()
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            skipped_files.append(file_number)
            return

        # Fill in the template
        prompt = prompt_template.format(case_study=file_content)

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
                    print(f"Processing file {file_number}, attempt {attempt}")
                    async with session.post(OPENAI_API_URL, headers=headers, json=payload) as response:
                        if response.status == 401:
                            print("Authentication failed: Invalid API key or key has expired")
                            return
                        elif response.status != 200:
                            error_content = await response.text()
                            print(f"API error for file {file_number}. HTTP Status: {response.status}. Error: {error_content}. Attempt: {attempt}")
                            await asyncio.sleep(2)
                            continue

                        resp_json = await response.json()
                        
                        try:
                            # Extract content from response
                            response_content = resp_json['choices'][0]['message']['content']
                            
                            # Parse the JSON content
                            structured_content = json.loads(response_content)
                            
                            # Validate required fields
                            if not all(key in structured_content for key in ['content', 'metadata']):
                                raise ValueError("Missing required fields in response")
                            
                            if not all(key in structured_content['metadata'] for key in [
                                'link', 'company_name', 'azure_services_used', 'outcomes',
                                'region', 'year', 'industry', 'summary'
                            ]):
                                raise ValueError("Missing required metadata fields")
                            
                            # Save output
                            with open(output_file_path, "w", encoding="utf-8") as outfile:
                                json.dump(structured_content, outfile, indent=4)
                            print(f"Successfully processed file {file_number}.txt")
                            break  # Exit loop on successful processing
                            
                        except (KeyError, json.JSONDecodeError, ValueError) as e:
                            print(f"Error parsing API response for file {file_number}: {e}")
                            if attempt == RETRY_LIMIT:
                                skipped_files.append(file_number)
                            continue

                except Exception as e:
                    print(f"Exception for file {file_number} on attempt {attempt}: {e}")
                    await asyncio.sleep(2)
        else:
            print(f"Failed to process file {file_number} after {RETRY_LIMIT} attempts.")
            skipped_files.append(file_number)

    async def process_all_files():
        """Process all txt files in the INPUT_DIR."""
        # Get list of all txt files and extract their numbers
        txt_files = [f for f in os.listdir(INPUT_DIR) if f.endswith('.txt')]
        file_numbers = sorted([int(f.split('.')[0]) for f in txt_files])
        
        if not file_numbers:
            print("No txt files found in AZURE directory")
            return
            
        total_files = len(file_numbers)
        print(f"Found {total_files} files to process")
        
        semaphore = asyncio.Semaphore(BATCH_SIZE)
        tasks = []
        
        async with aiohttp.ClientSession() as session:
            for file_num in file_numbers:
                tasks.append(process_file(file_num, semaphore, session))
            
            # Process files in batches
            completed = 0
            for batch in range(0, len(tasks), BATCH_SIZE):
                batch_tasks = tasks[batch:batch + BATCH_SIZE]
                await asyncio.gather(*batch_tasks)
                completed += len(batch_tasks)
                print(f"Progress: {completed}/{total_files} files processed")

        if skipped_files:
            print("Skipped file numbers:", skipped_files)
        else:
            print("All files processed successfully.")

    # Process all files
    await process_all_files()

if __name__ == "__main__":
    print("Starting Azure content rewriting with OpenAI")
    asyncio.run(rewrite_azure_content())
    print("\nProcessing completed!") 