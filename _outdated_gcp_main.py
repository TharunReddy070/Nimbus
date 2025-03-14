import os
import json
import time
import glob
import asyncio
import argparse
from dotenv import load_dotenv
from openai import AsyncOpenAI, OpenAI
import psycopg2
from psycopg2.extras import execute_values
import numpy as np

# Load environment variables
load_dotenv()

# Constants
NEON_DATABASE_URL = os.getenv("NEON_DATABASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
BATCH_SIZE = 3  # Optimal batch size based on benchmark
MAX_RETRIES = 3  # Maximum number of retries for API calls
GCP_TABLE_NAME = "gcp_case_studies"  # Separate table for GCP case studies

class RagSystem:
    def __init__(self, db_url, api_key):
        """Initialize the RAG system with database connection and OpenAI clients."""
        self.db_url = db_url
        self.conn = None
        self.cursor = None
        self.openai_client = OpenAI(api_key=api_key)
        self.async_openai_client = AsyncOpenAI(api_key=api_key)
    
    def connect_to_db(self):
        """Connect to the PostgreSQL database."""
        try:
            self.conn = psycopg2.connect(self.db_url)
            self.cursor = self.conn.cursor()
            print("Connected to database successfully")
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
        except Exception as e:
            print(f"Error enabling pgvector extension: {e}")
            self.conn.rollback()
    
    def create_table(self, table_name):
        """Create the case studies table if it doesn't exist."""
        try:
            self.cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id SERIAL PRIMARY KEY,
                    case_id TEXT UNIQUE,
                    content TEXT,
                    embedding vector({EMBEDDING_DIMENSIONS}),
                    link TEXT,
                    company_name TEXT,
                    region TEXT,
                    services_used TEXT[],
                    outcomes TEXT[],
                    summary TEXT,
                    year INTEGER,
                    industry TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS {table_name}_embedding_idx 
                ON {table_name} USING ivfflat (embedding vector_l2_ops)
                WITH (lists = 100);
            """)
            self.conn.commit()
            print(f"Table {table_name} created or already exists")
            return True
        except Exception as e:
            print(f"Error creating table: {e}")
            self.conn.rollback()
            return False
    
    def create_search_function(self, table_name):
        """Create or replace the function to search for similar case studies."""
        try:
            # Drop existing function if it exists
            drop_function_query = f"""
                DROP FUNCTION IF EXISTS search_{table_name}(vector, float, integer);
            """
            self.cursor.execute(drop_function_query)
            self.conn.commit()
            
            # Create search function using PL/pgSQL for better flexibility
            function_query = f"""
                CREATE OR REPLACE FUNCTION search_{table_name}(
                    query_embedding vector({EMBEDDING_DIMENSIONS}),
                    similarity_threshold float,
                    max_results integer
                )
                RETURNS TABLE (
                    id integer,
                    case_id text,
                    content text,
                    similarity float,
                    link text,
                    company_name text,
                    region text,
                    services_used text[],
                    outcomes text[],
                    summary text,
                    year integer,
                    industry text
                )
                LANGUAGE plpgsql
                AS $$
                BEGIN
                    RETURN QUERY
                    SELECT
                        t.id,
                        t.case_id,
                        t.content,
                        1 - (t.embedding <-> query_embedding) AS similarity,
                        t.link,
                        t.company_name,
                        t.region,
                        t.services_used,
                        t.outcomes,
                        t.summary,
                        t.year,
                        t.industry
                    FROM
                        {table_name} t
                    WHERE
                        1 - (t.embedding <-> query_embedding) > similarity_threshold
                    ORDER BY
                        similarity DESC
                    LIMIT max_results;
                END;
                $$;
            """
            self.cursor.execute(function_query)
            self.conn.commit()
            print(f"Search function for {table_name} created successfully")
            return True
        except Exception as e:
            print(f"Error creating search function: {e}")
            self.conn.rollback()
            return False
    
    async def generate_embedding_async(self, text, max_retries=3, base_delay=1):
        """Generate an embedding for a text using the OpenAI API with exponential backoff."""
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                response = await self.async_openai_client.embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=text
                )
                return response.data[0].embedding
            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    print(f"Failed to generate embedding after {max_retries} attempts: {e}")
                    return None
                
                # Exponential backoff with jitter
                delay = base_delay * (2 ** (retry_count - 1)) * (0.5 + 0.5 * np.random.random())
                print(f"Retrying embedding generation in {delay:.2f} seconds... (Attempt {retry_count}/{max_retries})")
                await asyncio.sleep(delay)
    
    async def process_batch_async(self, texts):
        """Process a batch of texts to generate embeddings asynchronously."""
        try:
            tasks = [self.generate_embedding_async(text, MAX_RETRIES) for text in texts]
            return await asyncio.gather(*tasks)
        except Exception as e:
            print(f"Error in batch processing: {e}")
            return [None] * len(texts)
    
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
                item['metadata'].get('aws_services_used', []),  # For GCP case studies, this will be GCP services
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
            skipped_count = len(case_studies) - inserted_count
            
            print(f"Batch results: {inserted_count} inserted, {skipped_count} skipped")
            
            return True
        except Exception as e:
            print(f"Error batch inserting case studies: {e}")
            self.conn.rollback()
            return False
    
    def search_case_studies(self, table_name, query_text, threshold=0.7, limit=5):
        """Search for case studies similar to the query text."""
        try:
            # Generate embedding for the query text
            response = self.openai_client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=query_text
            )
            query_embedding = response.data[0].embedding
            print(f"Generated embedding with {len(query_embedding)} dimensions")
            
            # Execute search query with proper vector casting
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
            formatted_results = []
            for row in results:
                formatted_results.append({
                    'id': row[0],
                    'case_id': row[1],
                    'content': row[2],
                    'similarity': row[3],
                    'link': row[4],
                    'company_name': row[5],
                    'region': row[6],
                    'services_used': row[7],
                    'outcomes': row[8],
                    'summary': row[9],
                    'year': row[10],
                    'industry': row[11]
                })
            
            return formatted_results
        except Exception as e:
            print(f"Error searching case studies: {e}")
            return []
    
    def clean_table(self, table_name):
        """Clean (truncate) the table."""
        try:
            self.cursor.execute(f"TRUNCATE TABLE {table_name} RESTART IDENTITY;")
            self.conn.commit()
            print(f"Table {table_name} has been cleaned")
            return True
        except Exception as e:
            print(f"Error cleaning table: {e}")
            self.conn.rollback()
            return False
    
    def drop_table(self, table_name):
        """Drop the table."""
        try:
            self.cursor.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE;")
            self.conn.commit()
            print(f"Table {table_name} has been dropped")
            return True
        except Exception as e:
            print(f"Error dropping table: {e}")
            self.conn.rollback()
            return False
    
    def process_gcp_file_pair(self, txt_file, json_file):
        """Process a pair of TXT and JSON files for a GCP case study."""
        try:
            # Extract content from txt file
            with open(txt_file, 'r') as f:
                content = f.read()
            
            # Extract metadata from json file
            with open(json_file, 'r') as f:
                metadata = json.load(f)
            
            # Get case ID from the filename (without extension)
            case_id = os.path.basename(txt_file).split('.')[0]
            
            return {
                'case_id': case_id,
                'content': content,
                'metadata': metadata
            }
        except Exception as e:
            print(f"Error processing file pair {txt_file}, {json_file}: {e}")
            return None

async def process_gcp_files(rag_system, table_name):
    """Process all GCP case study file pairs in the gcp directory."""
    # Get all TXT files
    txt_files = glob.glob(os.path.join('gcp', '*.txt'))
    
    print(f"Found {len(txt_files)} TXT files in the gcp directory")
    
    # Measure timing
    start_time = time.time()
    
    # Process files
    processed_count = 0
    failed_count = 0
    skipped_count = 0
    
    # Process in batches
    for i in range(0, len(txt_files), BATCH_SIZE):
        batch_files = txt_files[i:i+BATCH_SIZE]
        
        # Process each file pair in the batch
        case_studies = []
        for txt_file in batch_files:
            # Find corresponding JSON file
            json_file = txt_file.replace('.txt', '.json')
            
            if os.path.exists(json_file):
                case_study = rag_system.process_gcp_file_pair(txt_file, json_file)
                if case_study:
                    case_studies.append(case_study)
                else:
                    failed_count += 1
            else:
                print(f"No matching JSON file found for {txt_file}")
                skipped_count += 1
        
        if not case_studies:
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
        elapsed = time.time() - start_time
        files_processed = i + len(batch_files)
        
        if files_processed > 0:
            avg_time_per_file = elapsed / files_processed
            remaining_files = len(txt_files) - files_processed
            estimated_time_remaining = remaining_files * avg_time_per_file
            
            print(f"Progress: {files_processed}/{len(txt_files)} files processed")
            print(f"Stats: {processed_count} inserted, {failed_count} failed, {skipped_count} skipped")
            print(f"Time elapsed: {elapsed:.2f}s, Estimated time remaining: {estimated_time_remaining:.2f}s")
    
    # Print final stats
    total_elapsed = time.time() - start_time
    print("\n--- PROCESSING COMPLETE ---")
    print(f"Total files processed: {len(txt_files)}")
    print(f"Successfully processed: {processed_count}")
    print(f"Failed: {failed_count}")
    print(f"Skipped: {skipped_count}")
    print(f"Total time: {total_elapsed:.2f} seconds")
    
    return processed_count, failed_count, skipped_count

async def main():
    """Main function to run the RAG system for GCP case studies."""
    parser = argparse.ArgumentParser(description='Process GCP case studies and create embeddings.')
    parser.add_argument('--clean', action='store_true', help='Clean the table before processing')
    parser.add_argument('--drop', action='store_true', help='Drop and recreate the table before processing')
    parser.add_argument('--search', type=str, help='Search GCP case studies with the given query')
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
            rag_system.drop_table(GCP_TABLE_NAME)
        
        # Create table
        rag_system.create_table(GCP_TABLE_NAME)
        
        # Create search function
        rag_system.create_search_function(GCP_TABLE_NAME)
        
        # Clean the table if requested
        if args.clean:
            print("\n--- CLEANING TABLE ---")
            rag_system.clean_table(GCP_TABLE_NAME)
        
        # Search if requested
        if args.search:
            print(f"\n--- SEARCHING GCP CASE STUDIES: '{args.search}' ---")
            print(f"Parameters: threshold={args.threshold}, limit={args.limit}")
            
            results = rag_system.search_case_studies(
                GCP_TABLE_NAME,
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
                print(f"Services: {', '.join(result['services_used'])}")
        else:
            # Process files
            print("\n--- PROCESSING GCP CASE STUDIES ---")
            await process_gcp_files(rag_system, GCP_TABLE_NAME)
    
    finally:
        # Close the database connection
        rag_system.close_connection()

if __name__ == "__main__":
    asyncio.run(main())
