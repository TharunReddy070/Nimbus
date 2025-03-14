#!/usr/bin/env python3

import os
import csv
import logging
import psycopg2
import pandas as pd
import asyncio
import glob
import json
from pathlib import Path
from scrapping.aws_links import scrape_aws_case_studies
from scrapping.aws_links_to_pdf import save_pages_as_pdf_and_links
from scrapping.append_pdf_to_txt import append_pdf_to_txt
from scrapping.aws_content_rewriting import rewrite_aws_content
from openai import AsyncOpenAI
from psycopg2.extras import execute_values
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("aws_workflow.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Constants
NEON_DATABASE_URL = os.getenv("NEON_DATABASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PROVIDER = "aws"
CASE_STUDIES_TABLE = "case_studies"
SCRAPING_DIR = Path("scrapping")
LINKS_CSV_PATH = SCRAPING_DIR / "1.csv"  # File will be in scrapping directory
AWS_JSON_DIR = SCRAPING_DIR / "aws_json"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536

def connect_to_db():
    """Connect to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(NEON_DATABASE_URL)
        cursor = conn.cursor()
        logger.info("Connected to database successfully")
        return conn, cursor
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return None, None

def filter_existing_links(conn, cursor):
    """
    Compare links in CSV with links in the case_studies table.
    Keep only links that don't exist in the database.
    """
    logger.info("Filtering out links that already exist in the database")
    
    try:
        # Check if the table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'case_studies'
            );
        """)
        
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            logger.info("Table case_studies does not exist yet. No filtering needed.")
            return True
        
        # Read the CSV file
        df = pd.read_csv(LINKS_CSV_PATH)
        
        # Get the list of links from the CSV
        csv_links = df['link'].tolist()
        logger.info("CSV Links:")
        for link in csv_links:
            logger.info(f"CSV: {link}")
        
        # Query the database for existing links
        cursor.execute("SELECT link FROM case_studies WHERE link IS NOT NULL")
        db_links = [row[0] for row in cursor.fetchall()]
        
        # Sample some database links for verification
        logger.info("\nSample of DB Links (first 5):")
        for link in db_links[:5]:
            logger.info(f"DB: {link}")
            
        # Find links that don't exist in the database
        new_links = [link for link in csv_links if link not in db_links]
        
        # Create a new DataFrame with only new links
        new_df = pd.DataFrame({
            'link': new_links,
            'is_scraped': False,
            'is_embedded': False
        })
        
        # Save the updated CSV
        new_df.to_csv(LINKS_CSV_PATH, index=False)
        
        logger.info(f"Total links in CSV: {len(csv_links)}")
        logger.info(f"Total links in DB: {len(db_links)}")
        logger.info(f"New links kept: {len(new_links)}")
        return True
    except Exception as e:
        logger.error(f"Failed to filter existing links: {e}")
        return False

def cleanup_temp_files():
    """Step 9: Clean up temporary files and directories."""
    logger.info("Step 9: Cleaning up temporary files and directories")
    
    try:
        # Define paths to clean
        aws_json_dir = SCRAPING_DIR / "aws_json"
        aws_pdf_dir = SCRAPING_DIR / "aws_pdf"
        csv_file = LINKS_CSV_PATH
        
        # Delete aws_json directory
        if aws_json_dir.exists():
            for file in aws_json_dir.glob("*"):
                file.unlink()
            aws_json_dir.rmdir()
            logger.info(f"Deleted directory: {aws_json_dir}")
            
        # Delete aws_pdf directory
        if aws_pdf_dir.exists():
            for file in aws_pdf_dir.glob("*"):
                file.unlink()
            aws_pdf_dir.rmdir()
            logger.info(f"Deleted directory: {aws_pdf_dir}")
            
        # Delete 1.csv file
        if csv_file.exists():
            csv_file.unlink()
            logger.info(f"Deleted file: {csv_file}")
            
        logger.info("Cleanup completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        return False

async def update_case_studies_table():
    """Step 6: Update case_studies table with embeddings and metadata."""
    logger.info("Step 6: Updating case_studies table with embeddings and metadata")
    
    try:
        # Connect to database
        conn = psycopg2.connect(NEON_DATABASE_URL)
        cursor = conn.cursor()
        
        # Get initial row count
        cursor.execute(f"SELECT COUNT(*) FROM {CASE_STUDIES_TABLE}")
        initial_count = cursor.fetchone()[0]
        logger.info(f"Initial row count in {CASE_STUDIES_TABLE}: {initial_count}")
        
        # Initialize OpenAI client
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        
        # Get all JSON files
        json_files = glob.glob(str(AWS_JSON_DIR / "*.json"))
        logger.info(f"Found {len(json_files)} JSON files to process")
        
        processed_count = 0
        for json_file in json_files:
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                
                # Extract content and metadata from the JSON structure
                message_content = data['choices'][0]['message']['content']
                parsed_content = json.loads(message_content)
                
                content = parsed_content['content']
                metadata = parsed_content['metadata']
                
                # Generate embedding
                embedding_response = await client.embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=content
                )
                embedding = embedding_response.data[0].embedding
                
                # Get case_id from filename
                case_id = Path(json_file).stem
                
                # First check if this case_id exists
                cursor.execute(f"SELECT case_id FROM {CASE_STUDIES_TABLE} WHERE case_id = %s", (case_id,))
                exists = cursor.fetchone()
                
                if exists:
                    # Update existing record
                    update_query = f"""
                        UPDATE {CASE_STUDIES_TABLE} SET
                            content = %s,
                            embedding = %s,
                            link = %s,
                            company_name = %s,
                            region = %s,
                            services_used = %s,
                            outcomes = %s,
                            summary = %s,
                            year = %s,
                            industry = %s
                        WHERE case_id = %s;
                    """
                    cursor.execute(update_query, (
                        content,
                        embedding,
                        metadata.get('link'),
                        metadata.get('company_name'),
                        metadata.get('region'),
                        metadata.get('aws_services_used'),
                        metadata.get('outcomes'),
                        metadata.get('summary'),
                        metadata.get('year'),
                        metadata.get('industry'),
                        case_id
                    ))
                    logger.info(f"Updated existing record for case_id: {case_id}")
                else:
                    # Insert new record
                    insert_query = f"""
                        INSERT INTO {CASE_STUDIES_TABLE} (
                            case_id, content, embedding, link, company_name, region,
                            services_used, outcomes, summary, year, industry
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        );
                    """
                    cursor.execute(insert_query, (
                        case_id,
                        content,
                        embedding,
                        metadata.get('link'),
                        metadata.get('company_name'),
                        metadata.get('region'),
                        metadata.get('aws_services_used'),
                        metadata.get('outcomes'),
                        metadata.get('summary'),
                        metadata.get('year'),
                        metadata.get('industry')
                    ))
                    logger.info(f"Inserted new record for case_id: {case_id}")
                
                conn.commit()
                processed_count += 1
                logger.info(f"Processed {processed_count}/{len(json_files)} files")
                
            except Exception as e:
                logger.error(f"Error processing {json_file}: {e}")
                continue
        
        # Get final row count
        cursor.execute(f"SELECT COUNT(*) FROM {CASE_STUDIES_TABLE}")
        final_count = cursor.fetchone()[0]
        logger.info(f"Final row count in {CASE_STUDIES_TABLE}: {final_count}")
        logger.info(f"Added {final_count - initial_count} new records")
        
    except Exception as e:
        logger.error(f"Error in update_case_studies_table: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def update_csv_embedded_status():
    """Step 7: Update is_embedded status in 1.csv."""
    logger.info("Step 7: Updating is_embedded status in 1.csv")
    
    try:
        # Read the CSV file
        df = pd.read_csv(LINKS_CSV_PATH)
        
        # Update is_embedded to True for all rows
        df['is_embedded'] = True
        
        # Save back to CSV
        df.to_csv(LINKS_CSV_PATH, index=False)
        logger.info(f"Updated {len(df)} rows in {LINKS_CSV_PATH}")
        
    except Exception as e:
        logger.error(f"Error updating CSV embedded status: {e}")
        raise

def update_links_table():
    logger.info("Step 8: Updating aws_links table")
    
    try:
        # Connect to database
        conn = psycopg2.connect(NEON_DATABASE_URL)
        cursor = conn.cursor()
        
        # Read the CSV file
        df = pd.read_csv(LINKS_CSV_PATH)
        
        # Check for links with is_embedded or is_scraped as False
        unprocessed_links = df[~(df['is_embedded'] & df['is_scraped'])]
        
        if not unprocessed_links.empty:
            logger.warning("Found links that are not fully processed:")
            for _, row in unprocessed_links.iterrows():
                logger.warning(f"Link: {row['link']}")
                logger.warning(f"is_scraped: {row['is_scraped']}")
                logger.warning(f"is_embedded: {row['is_embedded']}")
            logger.warning(f"Total unprocessed links: {len(unprocessed_links)}")
        else:
            logger.info("All links have been fully processed (scraped and embedded)")
        
    except Exception as e:
        logger.error(f"Error updating links table: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# def delete_test_rows():
#     """Step 8.5: Delete rows from case_studies table that match links in 1.csv."""
#     logger.info("Step 8.5: Deleting test rows from case_studies table")
    
#     try:
#         # Connect to database
#         conn = psycopg2.connect(NEON_DATABASE_URL)
#         cursor = conn.cursor()
        
#         # Get initial count
#         cursor.execute(f"SELECT COUNT(*) FROM {CASE_STUDIES_TABLE}")
#         initial_count = cursor.fetchone()[0]
#         logger.info(f"Initial row count in {CASE_STUDIES_TABLE}: {initial_count}")
        
#         # Read the CSV file
#         df = pd.read_csv(LINKS_CSV_PATH)
#         test_links = df['link'].tolist()
#         logger.info(f"Found {len(test_links)} links in CSV to process")
        
#         # Log the links that will be deleted
#         logger.info("Links to be deleted:")
#         for link in test_links[:5]:  # Show first 5 links
#             logger.info(f"- {link}")
#         if len(test_links) > 5:
#             logger.info(f"... and {len(test_links) - 5} more")
        
#         # Delete matching rows
#         placeholders = ','.join(['%s'] * len(test_links))
#         delete_query = f"""
#             DELETE FROM {CASE_STUDIES_TABLE}
#             WHERE link IN ({placeholders})
#             RETURNING id, link;
#         """
        
#         cursor.execute(delete_query, test_links)
#         deleted_rows = cursor.fetchall()
#         conn.commit()
        
#         # Log deleted rows
#         logger.info("\nDeleted rows:")
#         for row in deleted_rows[:5]:  # Show first 5 deleted rows
#             logger.info(f"Deleted ID: {row[0]}, Link: {row[1]}")
#         if len(deleted_rows) > 5:
#             logger.info(f"... and {len(deleted_rows) - 5} more rows deleted")
        
#         # Get final count
#         cursor.execute(f"SELECT COUNT(*) FROM {CASE_STUDIES_TABLE}")
#         final_count = cursor.fetchone()[0]
        
#         # Summary
#         logger.info("\nDeletion Summary:")
#         logger.info(f"Initial count: {initial_count}")
#         logger.info(f"Rows deleted: {len(deleted_rows)}")
#         logger.info(f"Final count: {final_count}")
        
#         return True
        
#     except Exception as e:
#         logger.error(f"Error deleting test rows: {e}")
#         if conn:
#             conn.rollback()
#         return False
#     finally:
#         if cursor:
#             cursor.close()
#         if conn:
#             conn.close()

async def main():
    """Main function to run all steps of the workflow."""
        
    logger.info("Starting AWS workflow")
    
    # Step 1: Run aws_links.py to scrape links
    logger.info("Step 1: Running AWS case study link scraper")
    csv_path = await scrape_aws_case_studies()
    logger.info(f"Links saved to: {csv_path}")
    
    # Step 2: Connect to database and filter existing links
    logger.info("Step 2: Connecting to database and filtering existing links")
    conn, cursor = connect_to_db()
    if not conn or not cursor:
        logger.error("Failed to connect to database")
        return
    
    try:
        if not filter_existing_links(conn, cursor):
            logger.error("Failed to filter existing links")
            return
        
        # Step 3: Save pages as PDFs
        logger.info("Step 3: Saving pages as PDFs")
        await save_pages_as_pdf_and_links()
        
        logger.info("Step 3 completed successfully!")
    
    finally:
        # Close database connection
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            logger.info("Database connection closed")

    # Step 4: Append PDF content to TXT files
    logger.info("Step 4: Appending PDF content to TXT files")
    try:
        await append_pdf_to_txt()
        logger.info("Step 4 completed successfully!")
    except Exception as e:
        logger.error(f"Failed to append PDF content to TXT files: {e}")
        return

    # Step 5: Content rewriting
    logger.info("Step 5: Rewriting AWS content")
    try:
        await rewrite_aws_content()
        logger.info("Step 5 completed successfully!")
    except Exception as e:
        logger.error(f"Failed to rewrite AWS content: {e}")
        return

    # Step 6: Update case_studies table
    logger.info("Step 6: Updating case_studies table")
    try:
        await update_case_studies_table()
        logger.info("Step 6 completed successfully!")
    except Exception as e:
        logger.error(f"Failed to update case_studies table: {e}")
        return

    # Step 7: Update CSV embedded status
    logger.info("Step 7: Updating CSV embedded status")
    try:
        update_csv_embedded_status()
        logger.info("Step 7 completed successfully!")
    except Exception as e:
        logger.error(f"Failed to update CSV embedded status: {e}")
        return

    # Step 8: Update links table
    logger.info("Step 8: Updating links table")
    try:
        update_links_table()
        logger.info("Step 8 completed successfully!")
    except Exception as e:
        logger.error(f"Failed to update links table: {e}")
        return

    # # Step 8.5: Delete test rows
    # logger.info("Step 8.5: Deleting test rows")
    # try:
    #     if delete_test_rows():
    #         logger.info("Step 8.5 completed successfully!")
    #     else:
    #         logger.error("Failed to delete test rows")
    #         return
    # except Exception as e:
    #     logger.error(f"Failed during test rows deletion: {e}")
    #     return

    # Step 9: Cleanup
    logger.info("Step 9: Running cleanup")
    try:
        if cleanup_temp_files():
            logger.info("Step 9 completed successfully!")
        else:
            logger.error("Failed to complete cleanup")
    except Exception as e:
        logger.error(f"Failed during cleanup: {e}")

    logger.info("All steps completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
