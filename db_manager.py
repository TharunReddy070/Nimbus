import sqlite3
import os
from pathlib import Path

class DatabaseManager:
    def __init__(self, db_path="case_studies.db"):
        """Initialize the database connection and create tables if needed"""
        # Create directory for database if it doesn't exist
        db_dir = Path("database")
        db_dir.mkdir(exist_ok=True)
        
        # Full path to the database
        db_full_path = db_dir / db_path
        
        # Initialize connection
        self.conn = sqlite3.connect(str(db_full_path))
        self.create_tables()
    
    def create_tables(self):
        """Create necessary tables if they don't exist"""
        cursor = self.conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS case_studies (
            id INTEGER,
            provider TEXT,
            link TEXT,
            pdf_path TEXT,
            txt_path TEXT,
            content TEXT,
            is_embedded INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (provider, id)
        )
        ''')
        self.conn.commit()
    
    def save_content(self, id, provider, link, pdf_path, txt_path, content, is_embedded=0):
        """Save case study content to database"""
        cursor = self.conn.cursor()
        cursor.execute('''
        INSERT OR REPLACE INTO case_studies (id, provider, link, pdf_path, txt_path, content, is_embedded, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (id, provider, link, pdf_path, txt_path, content, is_embedded))
        self.conn.commit()
    
    def save_error_record(self, id, provider, link, error):
        """Save a record for a failed case study to maintain ID sequence"""
        cursor = self.conn.cursor()
        # Use placeholder values for paths and content
        pdf_path = f"ERROR_{id}.pdf"
        txt_path = f"ERROR_{id}.txt"
        content = f"ERROR: {error}"
        is_embedded = -1  # Use -1 to indicate an error record
        
        cursor.execute('''
        INSERT OR REPLACE INTO case_studies (id, provider, link, pdf_path, txt_path, content, is_embedded, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (id, provider, link, pdf_path, txt_path, content, is_embedded))
        self.conn.commit()
    
    def get_last_id(self, provider):
        """Get the highest ID from the database for a specific provider"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT MAX(id) FROM case_studies WHERE provider = ?", (provider,))
            result = cursor.fetchone()
            if result and result[0]:
                return result[0]
            return 0
        except Exception as e:
            print(f"Error retrieving last ID from database for provider {provider}: {str(e)}")
            return 0
    
    def get_case_studies(self, provider=None, limit=None):
        """Get case studies with newest first, optionally filtered by provider"""
        try:
            cursor = self.conn.cursor()
            # Set row_factory to return dictionaries
            self.conn.row_factory = sqlite3.Row
            cursor = self.conn.cursor()
            
            query = "SELECT * FROM case_studies"
            params = []
            
            if provider:
                query += " WHERE provider = ?"
                params.append(provider)
                
            query += " ORDER BY created_at DESC"
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
                
            cursor.execute(query, params)
            results = [dict(row) for row in cursor.fetchall()]
            
            # Reset row_factory
            self.conn.row_factory = None
            
            return results
        except Exception as e:
            print(f"Error retrieving case studies: {str(e)}")
            return []
    
    def update_embedding_status(self, id, is_embedded=1):
        """Update the embedding status of a case study"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            UPDATE case_studies 
            SET is_embedded = ? 
            WHERE id = ?
            ''', (is_embedded, id))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error updating embedding status: {str(e)}")
            return False
    
    def get_unembedded_case_studies(self, provider=None, limit=None):
        """Get case studies that haven't been embedded yet, optionally filtered by provider"""
        try:
            # Set row_factory to return dictionaries
            self.conn.row_factory = sqlite3.Row
            cursor = self.conn.cursor()
            
            query = "SELECT * FROM case_studies WHERE is_embedded = 0"
            params = []
            
            if provider:
                query += " AND provider = ?"
                params.append(provider)
                
            query += " ORDER BY created_at DESC"
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
                
            cursor.execute(query, params)
            results = [dict(row) for row in cursor.fetchall()]
            
            # Reset row_factory
            self.conn.row_factory = None
            
            return results
        except Exception as e:
            print(f"Error retrieving unembedded case studies: {str(e)}")
            return []
    
    def link_exists(self, provider, link):
        """Check if a link already exists in the database for a specific provider"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM case_studies WHERE provider = ? AND link = ?", 
                (provider, link)
            )
            result = cursor.fetchone()
            return result[0] > 0
        except Exception as e:
            print(f"Error checking if link exists for provider {provider}: {str(e)}")
            return False
    
    def get_error_records(self, provider=None, limit=None):
        """Get case studies that failed processing (is_embedded = -1), optionally filtered by provider"""
        try:
            # Set row_factory to return dictionaries
            self.conn.row_factory = sqlite3.Row
            cursor = self.conn.cursor()
            
            query = "SELECT * FROM case_studies WHERE is_embedded = -1"
            params = []
            
            if provider:
                query += " AND provider = ?"
                params.append(provider)
                
            query += " ORDER BY created_at DESC"
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
                
            cursor.execute(query, params)
            results = [dict(row) for row in cursor.fetchall()]
            
            # Reset row_factory
            self.conn.row_factory = None
            
            return results
        except Exception as e:
            print(f"Error retrieving error records: {str(e)}")
            return []
    
    def close(self):
        """Close the database connection"""
        if hasattr(self, 'conn'):
            self.conn.close()