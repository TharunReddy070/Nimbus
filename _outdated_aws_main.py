#!/usr/bin/env python3
import os
import json
import time
import glob
import argparse
import psycopg2
import asyncio
import concurrent.futures
from dotenv import load_dotenv
from openai import AsyncOpenAI, OpenAI
from psycopg2.extras import execute_values

# Load environment variables
load_dotenv()

# Get configuration from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NEON_DATABASE_URL = os.getenv("NEON_DATABASE_URL")

# Constants
EMBEDDING_MODEL = "text-embedding-3-small"  # OpenAI's model with 1536 dimensions
EMBEDDING_DIMENSIONS = 1536
MAIN_TABLE_NAME = "case_studies"
BATCH_SIZE = 3  # Optimized batch size for balance between performance and reliability

class RagSystem:
    def __init__(self, db_url, api_key):
        """Initialize the RAG system with database and OpenAI API credentials."""
        self.db_url = db_url
        self.openai_client = OpenAI(api_key=api_key)
        self.async_openai_client = AsyncOpenAI(api_key=api_key)
        self.conn = None
        self.cursor = None
    
    def connect_to_db(self):
        """Connect to the Neon PostgreSQL database."""
        try:
            self.conn = psycopg2.connect(self.db_url)
            self.cursor = self.conn.cursor()
            print("Connected to Neon PostgreSQL database")
            return True
        except Exception as e:
            print(f"Error connecting to database: {e}")
            return False
    
    def close_connection(self):
        """Close the database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
            print("Database connection closed")
    
    def enable_pgvector_extension(self):
        """Enable the pgvector extension in PostgreSQL."""
        try:
            self.cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            self.conn.commit()
            print("pgvector extension enabled")
            return True
        except Exception as e:
            print(f"Error enabling pgvector extension: {e}")
            self.conn.rollback()
            return False
    
    def create_table(self, table_name):
        """Create a table to store case studies with vector embeddings."""
        try:
            self.cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id SERIAL PRIMARY KEY,
                    case_id TEXT UNIQUE,
                    content TEXT NOT NULL,
                    embedding VECTOR({EMBEDDING_DIMENSIONS}) NOT NULL,
                    link TEXT,
                    company_name TEXT,
                    region TEXT,
                    services_used TEXT[],
                    outcomes TEXT[],
                    summary TEXT,
                    year INTEGER,
                    industry TEXT
                );
            """)
            
            # Create index for similarity search
            self.cursor.execute(f"""
                CREATE INDEX IF NOT EXISTS {table_name}_embedding_idx
                ON {table_name} USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100);
            """)
            
            self.conn.commit()
            print(f"Table {table_name} created with pgvector index")
            return True
        except Exception as e:
            print(f"Error creating table: {e}")
            self.conn.rollback()
            return False
    
    def create_search_function(self, table_name):
        """Create a SQL function to search case studies by vector similarity."""
        try:
            # Drop existing function if it exists to ensure clean creation
            self.cursor.execute(f"""
                DROP FUNCTION IF EXISTS search_{table_name} CASCADE;
            """)
            
            # Create a new search function with explicit VECTOR type handling
            self.cursor.execute(f"""
                CREATE OR REPLACE FUNCTION search_{table_name}(
                    query_embedding VECTOR({EMBEDDING_DIMENSIONS}),
                    match_threshold FLOAT,
                    match_count INT
                )
                RETURNS TABLE(
                    id INTEGER,
                    case_id TEXT,
                    content TEXT,
                    link TEXT,
                    company_name TEXT,
                    region TEXT,
                    services_used TEXT[],
                    outcomes TEXT[],
                    summary TEXT,
                    similarity FLOAT
                )
                LANGUAGE plpgsql
                AS $$
                BEGIN
                    RETURN QUERY
                    SELECT
                        t.id,
                        t.case_id,
                        t.content,
                        t.link,
                        t.company_name,
                        t.region,
                        t.services_used,
                        t.outcomes,
                        t.summary,
                        1 - (t.embedding <=> query_embedding) AS similarity
                    FROM {table_name} t
                    WHERE 1 - (t.embedding <=> query_embedding) > match_threshold
                    ORDER BY t.embedding <=> query_embedding
                    LIMIT match_count;
                END;
                $$;
            """)
            
            self.conn.commit()
            print(f"Search function for {table_name} created")
            return True
        except Exception as e:
            print(f"Error creating search function: {e}")
            self.conn.rollback()
            return False
    
    async def generate_embedding_async(self, text, max_retries=3, base_delay=1):
        """Generate an embedding vector asynchronously with retries."""
        for attempt in range(max_retries):
            try:
                response = await self.async_openai_client.embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=text
                )
                embedding = response.data[0].embedding
                return embedding
            except Exception as e:
                delay = base_delay * (2 ** attempt)  # Exponential backoff
                print(f"Attempt {attempt+1}/{max_retries} failed to generate embedding asynchronously: {e}")
                if attempt < max_retries - 1:  # Don't wait after the last attempt
                    print(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
        print(f"Failed to generate embedding asynchronously after {max_retries} attempts")
        return None
    
    async def process_batch_async(self, texts):
        """Process a batch of texts to generate embeddings concurrently."""
        tasks = [self.generate_embedding_async(text) for text in texts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results to handle exceptions
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                print(f"Error in batch processing: {result}")
                processed_results.append(None)
            else:
                processed_results.append(result)
        
        return processed_results
    
    def batch_insert_case_studies(self, table_name, case_studies):
        """Insert multiple case studies in a batch operation."""
        try:
            # Prepare data for batch insertion
            values = [(
                item['case_id'],
                item['content'],
                item['embedding'],
                item['metadata'].get('link'),
                item['metadata'].get('company_name'),
                item['metadata'].get('region'),
                item['metadata'].get('aws_services_used', []),
                item['metadata'].get('outcomes', []),
                item['metadata'].get('summary'),
                item['metadata'].get('year'),
                item['metadata'].get('industry')
            ) for item in case_studies]
            
            # Execute batch insertion
            execute_values(
                self.cursor,
                f"""
                INSERT INTO {table_name} (
                    case_id, content, embedding, link, company_name, region, 
                    services_used, outcomes, summary, year, industry
                ) VALUES %s
                ON CONFLICT (case_id) DO NOTHING
                RETURNING id
                """,
                values,
                template="(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            )
            
            results = self.cursor.fetchall()
            self.conn.commit()
            
            inserted_count = len(results)
            if inserted_count > 0:
                print(f"Batch inserted {inserted_count} new case studies")
            else:
                print(f"No new case studies inserted (all {len(case_studies)} already exist)")
            
            return True
        except Exception as e:
            print(f"Error batch inserting case studies: {e}")
            self.conn.rollback()
            return False
    
    def search_case_studies(self, table_name, query_text, threshold=0.7, limit=5):
        """Search for case studies similar to the query text."""
        # Generate embedding for the query text
        try:
            response = self.openai_client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=query_text
            )
            query_embedding = response.data[0].embedding
            
            # Use the search function to find similar case studies
            query = f"""
                SELECT * FROM search_{table_name}(
                    %s::vector({EMBEDDING_DIMENSIONS}), 
                    %s, 
                    %s
                );
            """
            self.cursor.execute(query, (query_embedding, threshold, limit))
            
            results = self.cursor.fetchall()
            
            # Format results
            columns = [desc[0] for desc in self.cursor.description]
            results_list = []
            for row in results:
                results_list.append(dict(zip(columns, row)))
            
            return results_list
        except Exception as e:
            print(f"Error searching case studies: {e}")
            import traceback
            traceback.print_exc()
            self.conn.rollback()  # Ensure transaction is rolled back on error
            return []
    
    def clean_table(self, table_name):
        """Clean (truncate) the specified table."""
        try:
            self.cursor.execute(f"TRUNCATE TABLE {table_name} RESTART IDENTITY;")
            self.conn.commit()
            print(f"Table {table_name} has been truncated")
            return True
        except Exception as e:
            print(f"Error cleaning table: {e}")
            self.conn.rollback()
            return False
    
    def drop_table(self, table_name):
        """Drop the specified table."""
        try:
            self.cursor.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE;")
            self.conn.commit()
            print(f"Table {table_name} has been dropped")
            return True
        except Exception as e:
            print(f"Error dropping table: {e}")
            self.conn.rollback()
            return False
    
    def process_json_file(self, file_path):
        """Process a single JSON file and extract content and metadata."""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Extract the content from the JSON structure
            message_content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            if message_content:
                # The content is actually a JSON string within the message content
                try:
                    parsed_content = json.loads(message_content)
                    content = parsed_content.get('content', '')
                    metadata = parsed_content.get('metadata', {})
                    
                    # Get file ID from the path (filename without extension)
                    file_id = os.path.basename(file_path).split('.')[0]
                    
                    return {
                        'case_id': file_id,
                        'content': content,
                        'metadata': metadata
                    }
                except json.JSONDecodeError:
                    print(f"Error decoding JSON content in file {file_path}")
                    return None
            else:
                print(f"No message content found in file {file_path}")
                return None
        except Exception as e:
            print(f"Error processing file {file_path}: {e}")
            return None

async def process_files(rag_system, table_name, start_idx=None, end_idx=None):
    """Process all JSON files in the output directory within the specified range."""
    if start_idx is not None and end_idx is not None:
        print(f"Processing files from {start_idx} to {end_idx}")
        # Process files in the specified range
        json_files = []
        for i in range(start_idx, end_idx + 1):
            file_path = os.path.join('output', f"{i}.json")
            if os.path.exists(file_path):
                json_files.append(file_path)
    else:
        print("Processing all JSON files in the output directory")
        # Process all files in the output directory
        json_files = glob.glob(os.path.join('output', '*.json'))
    
    print(f"Found {len(json_files)} files to process")
    
    # Measure timing
    start_time = time.time()
    
    # Process files
    processed_count = 0
    failed_count = 0
    skipped_count = 0
    
    # Process in batches
    for i in range(0, len(json_files), BATCH_SIZE):
        batch_files = json_files[i:i+BATCH_SIZE]
        
        # Process each file in the batch
        case_studies = []
        for file_path in batch_files:
            case_study = rag_system.process_json_file(file_path)
            if case_study:
                case_studies.append(case_study)
        
        if not case_studies:
            skipped_count += len(batch_files)
            continue
            
        # Get content for embedding
        content_batch = [item['content'] for item in case_studies]
        
        # Generate embeddings in batch
        embeddings = await rag_system.process_batch_async(content_batch)
        
        # Add embeddings to case studies
        items_to_insert = []
        for j, embedding in enumerate(embeddings):
            if embedding:
                case_studies[j]['embedding'] = embedding
                items_to_insert.append(case_studies[j])
            else:
                failed_count += 1
        
        # Insert batch into database
        if items_to_insert:
            rag_system.batch_insert_case_studies(table_name, items_to_insert)
            processed_count += len(items_to_insert)
        
        # Print progress
        if i % (BATCH_SIZE * 10) == 0 or i + BATCH_SIZE >= len(json_files):
            elapsed = time.time() - start_time
            files_processed = i + len(batch_files)
            percent_done = (files_processed / len(json_files)) * 100 if len(json_files) > 0 else 0
            estimated_total = (elapsed / files_processed) * len(json_files) if files_processed > 0 else 0
            time_left = max(0, estimated_total - elapsed)
            
            print(f"Progress: {files_processed}/{len(json_files)} files ({percent_done:.1f}%)")
            print(f"Stats: {processed_count} processed, {failed_count} failed, {skipped_count} skipped")
            print(f"Time: {elapsed:.2f}s elapsed, ~{time_left:.2f}s remaining")
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    print(f"\nProcessing completed:")
    print(f"Total files found: {len(json_files)}")
    print(f"Successfully processed: {processed_count}")
    print(f"Failed: {failed_count}")
    print(f"Skipped: {skipped_count}")
    print(f"Total time: {elapsed_time:.2f} seconds")
    print(f"Average time per file: {elapsed_time/len(json_files):.2f} seconds" if len(json_files) > 0 else "No files processed")
    
    return {
        "total_files": len(json_files),
        "processed_count": processed_count,
        "failed_count": failed_count,
        "skipped_count": skipped_count,
        "total_time": elapsed_time
    }

async def main():
    """Main function to run the RAG system."""
    parser = argparse.ArgumentParser(description='Process case studies and create embeddings.')
    parser.add_argument('--start', type=int, help='Starting index for file processing range')
    parser.add_argument('--end', type=int, help='Ending index for file processing range')
    parser.add_argument('--clean', action='store_true', help='Clean the table before processing')
    parser.add_argument('--drop', action='store_true', help='Drop and recreate the table before processing')
    parser.add_argument('--search', type=str, help='Search case studies with the given query')
    parser.add_argument('--threshold', type=float, default=0.6, help='Similarity threshold for search')
    parser.add_argument('--limit', type=int, default=5, help='Limit for search results')
    args = parser.parse_args()
    
    # Initialize RAG system
    rag_system = RagSystem(NEON_DATABASE_URL, OPENAI_API_KEY)
    
    # Connect to database
    if not rag_system.connect_to_db():
        return
    
    try:
        # Enable pgvector extension
        rag_system.enable_pgvector_extension()
        
        # Drop table if requested
        if args.drop:
            print("\n--- DROPPING TABLE ---")
            rag_system.drop_table(MAIN_TABLE_NAME)
        
        # Create main table
        rag_system.create_table(MAIN_TABLE_NAME)
        
        # Create search function
        rag_system.create_search_function(MAIN_TABLE_NAME)
        
        # Clean the table if requested
        if args.clean:
            print("\n--- CLEANING TABLE ---")
            rag_system.clean_table(MAIN_TABLE_NAME)
        
        # Search if requested
        if args.search:
            print(f"\n--- SEARCHING: '{args.search}' ---")
            print(f"Parameters: threshold={args.threshold}, limit={args.limit}")
            
            results = rag_system.search_case_studies(
                MAIN_TABLE_NAME,
                args.search,
                threshold=args.threshold,
                limit=args.limit
            )
            
            print(f"Found {len(results)} results:")
            for i, result in enumerate(results):
                print(f"\nResult {i+1} - Similarity: {result['similarity']:.4f}")
                print(f"Company: {result['company_name']}")
                print(f"Summary: {result['summary']}")
                print(f"Link: {result['link']}")
        else:
            # Process files
            print("\n--- PROCESSING FILES ---")
            await process_files(rag_system, MAIN_TABLE_NAME, args.start, args.end)
        
    finally:
        # Close database connection
        rag_system.close_connection()

if __name__ == "__main__":
    asyncio.run(main())
