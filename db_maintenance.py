#!/usr/bin/env python3

import os
import logging
import psycopg2
import argparse
import asyncio
from openai import AsyncOpenAI
from dotenv import load_dotenv
from psycopg2.extras import execute_values

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("db_maintenance.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Constants
NEON_DATABASE_URL = os.getenv("NEON_DATABASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CASE_STUDIES_TABLE = "case_studies"
LINKS_TABLE = "aws_links"
EMBEDDING_MODEL = "text-embedding-3-small"

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

def remove_duplicate_case_studies():
    """Remove duplicate rows from case_studies table based on links."""
    logger.info("Removing duplicates from case_studies table")
    
    try:
        conn, cursor = connect_to_db()
        if not conn or not cursor:
            return
            
        # Get initial count
        cursor.execute(f"SELECT COUNT(*) FROM {CASE_STUDIES_TABLE}")
        initial_count = cursor.fetchone()[0]
        logger.info(f"Initial row count: {initial_count}")
        
        # Delete duplicates keeping the latest entry
        delete_query = f"""
            DELETE FROM {CASE_STUDIES_TABLE}
            WHERE id IN (
                SELECT id FROM (
                    SELECT id,
                           ROW_NUMBER() OVER (PARTITION BY link ORDER BY id DESC) as rnum
                    FROM {CASE_STUDIES_TABLE}
                    WHERE link IS NOT NULL
                ) t
                WHERE t.rnum > 1
            );
        """
        
        cursor.execute(delete_query)
        deleted_count = cursor.rowcount
        conn.commit()
        
        # Get final count
        cursor.execute(f"SELECT COUNT(*) FROM {CASE_STUDIES_TABLE}")
        final_count = cursor.fetchone()[0]
        
        logger.info(f"Removed {deleted_count} duplicate rows")
        logger.info(f"Final row count: {final_count}")
        
    except Exception as e:
        logger.error(f"Error removing duplicates from case_studies: {e}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

async def test_similarity_search(query_text, threshold=0.7, limit=5):
    """Test similarity search functionality."""
    logger.info(f"Testing similarity search with query: {query_text}")
    logger.info(f"Parameters: threshold={threshold}, limit={limit}")
    
    try:
        # Initialize OpenAI client
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        
        # Generate embedding for query
        response = await client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=query_text
        )
        query_embedding = response.data[0].embedding
        
        # Connect to database
        conn, cursor = connect_to_db()
        if not conn or not cursor:
            return
            
        # Execute similarity search
        search_query = f"""
            SELECT 
                id,
                case_id,
                link,
                company_name,
                industry,
                summary,
                1 - (embedding <=> %s::vector) as similarity
            FROM {CASE_STUDIES_TABLE}
            WHERE 1 - (embedding <=> %s::vector) > %s
            ORDER BY similarity DESC
            LIMIT %s;
        """
        
        cursor.execute(search_query, (query_embedding, query_embedding, threshold, limit))
        results = cursor.fetchall()
        
        # Print results
        logger.info(f"\nFound {len(results)} results:")
        for i, row in enumerate(results, 1):
            logger.info(f"\nResult {i}:")
            logger.info(f"Similarity Score: {row[6]:.4f}")
            logger.info(f"Case ID: {row[1]}")
            logger.info(f"Company: {row[3]}")
            logger.info(f"Industry: {row[4]}")
            logger.info(f"Summary: {row[5]}")
            logger.info(f"Link: {row[2]}")
            
    except Exception as e:
        logger.error(f"Error in similarity search: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def print_table_info():
    """Print detailed information about the tables."""
    logger.info("Fetching table information")
    
    try:
        conn, cursor = connect_to_db()
        if not conn or not cursor:
            return
            
        # Get case_studies table info
        logger.info("\nCase Studies Table Info:")
        
        # Row count
        cursor.execute(f"SELECT COUNT(*) FROM {CASE_STUDIES_TABLE}")
        count = cursor.fetchone()[0]
        logger.info(f"Total rows: {count}")
        
        # Schema info
        cursor.execute(f"""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = '{CASE_STUDIES_TABLE}';
        """)
        columns = cursor.fetchall()
        logger.info("\nSchema:")
        for col in columns:
            logger.info(f"- {col[0]}: {col[1]}" + (f" (max length: {col[2]})" if col[2] else ""))
            
        # Sample data distribution
        logger.info("\nData Distribution:")
        
        # Companies count
        cursor.execute(f"SELECT COUNT(DISTINCT company_name) FROM {CASE_STUDIES_TABLE}")
        companies = cursor.fetchone()[0]
        logger.info(f"Unique companies: {companies}")
        
        # Industries count
        cursor.execute(f"SELECT COUNT(DISTINCT industry) FROM {CASE_STUDIES_TABLE}")
        industries = cursor.fetchone()[0]
        logger.info(f"Unique industries: {industries}")
        
        # AWS Links Table Info
        logger.info("\nAWS Links Table Info:")
        
        # Row count
        cursor.execute(f"SELECT COUNT(*) FROM {LINKS_TABLE}")
        count = cursor.fetchone()[0]
        logger.info(f"Total rows: {count}")
        
        # Schema info
        cursor.execute(f"""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = '{LINKS_TABLE}';
        """)
        columns = cursor.fetchall()
        logger.info("\nSchema:")
        for col in columns:
            logger.info(f"- {col[0]}: {col[1]}" + (f" (max length: {col[2]})" if col[2] else ""))
            
        # Status distribution
        cursor.execute(f"""
            SELECT 
                COUNT(*) FILTER (WHERE is_scraped) as scraped,
                COUNT(*) FILTER (WHERE is_embedded) as embedded,
                COUNT(*) as total
            FROM {LINKS_TABLE};
        """)
        stats = cursor.fetchone()
        logger.info("\nStatus Distribution:")
        logger.info(f"Total links: {stats[2]}")
        logger.info(f"Scraped: {stats[0]} ({(stats[0]/stats[2]*100):.2f}%)")
        logger.info(f"Embedded: {stats[1]} ({(stats[1]/stats[2]*100):.2f}%)")
        
    except Exception as e:
        logger.error(f"Error fetching table info: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

async def main():
    """Main function to run maintenance tasks."""
    parser = argparse.ArgumentParser(description='Database Maintenance Tasks')
    parser.add_argument('--remove-duplicates', action='store_true', help='Remove duplicate rows from both tables')
    parser.add_argument('--test-search', type=str, help='Test similarity search with given query')
    parser.add_argument('--threshold', type=float, default=0.0, help='Similarity threshold for search')
    parser.add_argument('--limit', type=int, default=5, help='Number of results to return')
    parser.add_argument('--table-info', action='store_true', help='Print detailed table information')
    
    args = parser.parse_args()
    
    if args.remove_duplicates:
        remove_duplicate_case_studies()
    
    if args.test_search:
        await test_similarity_search(args.test_search, args.threshold, args.limit)
    
    if args.table_info:
        print_table_info()
        
    if not any([args.remove_duplicates, args.test_search, args.table_info]):
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(main()) 