import os
import csv
import argparse
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database connection details
NEON_DATABASE_URL = os.getenv("NEON_DATABASE_URL")
print(f"Database URL configured: {'Yes' if NEON_DATABASE_URL else 'No'}")

def connect_to_db():
    """Connect to the PostgreSQL database."""
    print("\n=== CONNECTING TO DATABASE ===")
    try:
        conn = psycopg2.connect(NEON_DATABASE_URL)
        cursor = conn.cursor()
        print("Connected to database successfully!")
        return conn, cursor
    except Exception as e:
        print(f"ERROR: Failed to connect to database: {e}")
        return None, None

def check_table_exists(cursor, table_name):
    """Check if a table exists in the database."""
    print(f"\n=== CHECKING IF TABLE '{table_name}' EXISTS ===")
    try:
        cursor.execute(f"""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = %s
            );
        """, (table_name,))
        
        exists = cursor.fetchone()[0]
        print(f"Table '{table_name}' exists: {exists}")
        return exists
    except Exception as e:
        print(f"ERROR: Failed to check if table exists: {e}")
        return False

def create_links_table(conn, cursor, table_name):
    """Create a table for storing links."""
    print(f"\n=== CREATING TABLE '{table_name}' ===")
    try:
        cursor.execute(f"""
            CREATE TABLE {table_name} (
                id SERIAL PRIMARY KEY,
                link TEXT UNIQUE,
                is_embedded BOOLEAN,
                is_scraped BOOLEAN,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        print(f"Table '{table_name}' created successfully!")
        return True
    except Exception as e:
        print(f"ERROR: Failed to create table: {e}")
        conn.rollback()
        return False

def read_csv_file(file_path):
    """Read data from a CSV file."""
    print(f"\n=== READING CSV FILE: {file_path} ===")
    try:
        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            data = list(reader)
        
        print(f"Successfully read {len(data)} records from {file_path}")
        # Print first few records for verification
        if data:
            print("Sample records:")
            for i in range(min(3, len(data))):
                print(f"  - {data[i]}")
        return data
    except Exception as e:
        print(f"ERROR: Failed to read CSV file: {e}")
        return []

def insert_links_data(conn, cursor, table_name, data):
    """Insert data into the links table."""
    print(f"\n=== INSERTING DATA INTO '{table_name}' ===")
    
    if not data:
        print("No data to insert.")
        return 0
        
    try:
        inserted_count = 0
        skipped_count = 0
        error_count = 0
        
        print(f"Processing {len(data)} records...")
        
        for i, row in enumerate(data):
            try:
                # Convert string values to boolean
                is_embedded = row['is_embedded'].lower() == 'true'
                is_scraped = row['is_scraped'].lower() == 'true'
                
                query = f"""
                    INSERT INTO {table_name} (link, is_embedded, is_scraped)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (link) DO NOTHING
                    RETURNING id;
                """
                
                cursor.execute(query, (
                    row['link'],
                    is_embedded,
                    is_scraped
                ))
                
                result = cursor.fetchone()
                
                if result:
                    inserted_count += 1
                    if i < 3 or (i % 10 == 0):  # Log first 3 and then every 10th
                        print(f"  ✓ Inserted: {row['link'][:50]}... (ID: {result[0]})")
                else:
                    skipped_count += 1
                    if i < 3:  # Just log first few skips
                        print(f"  ↷ Skipped (already exists): {row['link'][:50]}...")
                
                # Commit every 10 records to avoid transaction timeouts
                if i > 0 and i % 10 == 0:
                    conn.commit()
                    print(f"  → Committed batch of 10 records (total processed: {i+1})")
                    
            except Exception as e:
                error_count += 1
                print(f"  ✗ Error inserting row {i}: {e}")
                print(f"    Row data: {row}")
        
        # Final commit for any remaining records
        conn.commit()
        
        print(f"\nInsertion complete!")
        print(f"  Inserted: {inserted_count} records")
        print(f"  Skipped: {skipped_count} records (already exist)")
        print(f"  Errors: {error_count} records")
        
        return inserted_count
    except Exception as e:
        print(f"ERROR: Failed during bulk insertion: {e}")
        conn.rollback()
        return 0

def ensure_csv_file_exists(provider):
    """Make sure the provider_links.csv file exists."""
    file_path = f"{provider}_links.csv"
    print(f"\n=== CHECKING FOR CSV FILE: {file_path} ===")
    
    if os.path.exists(file_path):
        print(f"File '{file_path}' exists!")
        return True
    
    # Create an empty CSV with the correct headers if it doesn't exist
    print(f"File '{file_path}' not found. Creating empty file...")
    try:
        with open(file_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['link', 'is_embedded', 'is_scraped'])
        print(f"Created empty '{file_path}' file with headers")
        return True
    except Exception as e:
        print(f"ERROR: Failed to create empty CSV file: {e}")
        return False

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Process provider links and store in database.')
    parser.add_argument('provider', choices=['aws', 'gcp'], help='Cloud provider (aws or gcp)')
    args = parser.parse_args()
    
    provider = args.provider.lower()
    table_name = f"{provider}_links"
    csv_file = f"{provider}_links.csv"
    
    print(f"\n=== LINKS PROCESSOR STARTED ===")
    print(f"Provider: {provider}")
    print(f"Table name: {table_name}")
    print(f"CSV file: {csv_file}")
    
    # Ensure the CSV file exists
    if not ensure_csv_file_exists(provider):
        return
    
    # Connect to the database
    conn, cursor = connect_to_db()
    if not conn or not cursor:
        return
    
    try:
        # Check if the table exists
        table_exists = check_table_exists(cursor, table_name)
        
        # Create the table if it doesn't exist
        if not table_exists:
            print(f"Table '{table_name}' does not exist. Creating...")
            if not create_links_table(conn, cursor, table_name):
                print(f"ERROR: Failed to create table '{table_name}'. Exiting.")
                return
        else:
            print(f"Table '{table_name}' already exists")
        
        # Read the CSV file
        data = read_csv_file(csv_file)
        if not data:
            print(f"ERROR: No data found in '{csv_file}'. Exiting.")
            return
        
        # Insert the data into the table
        inserted_count = insert_links_data(conn, cursor, table_name, data)
        
        print(f"\n=== LINKS PROCESSING COMPLETE ===")
        print(f"Provider: {provider}")
        print(f"Records processed: {len(data)}")
        print(f"Records inserted: {inserted_count}")
    
    finally:
        # Close the database connection
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        print("\nDatabase connection closed")

if __name__ == "__main__":
    main() 