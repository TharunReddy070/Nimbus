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
        is_embedded = -1  # Use -1 to indicate error
        
        cursor.execute('''
        INSERT OR REPLACE INTO case_studies (id, provider, link, pdf_path, txt_path, content, is_embedded, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (id, provider, link, pdf_path, txt_path, content, is_embedded))
        self.conn.commit()
    
    def get_case_studies(self, provider=None, limit=None):
        """Get case studies from database, optionally filtered by provider"""
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
        
        columns = [col[0] for col in cursor.description]
        results = []
        
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        
        return results
    
    def get_error_records(self, provider=None, limit=None):
        """Get error records from database, optionally filtered by provider"""
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
        
        columns = [col[0] for col in cursor.description]
        results = []
        
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        
        return results
    
    def get_unembedded_case_studies(self, provider=None, limit=None):
        """Get case studies that haven't been embedded yet"""
        cursor = self.conn.cursor()
        
        query = "SELECT * FROM case_studies WHERE is_embedded = 0"
        params = []
        
        if provider:
            query += " AND provider = ?"
            params.append(provider)
        
        query += " ORDER BY created_at ASC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor.execute(query, params)
        
        columns = [col[0] for col in cursor.description]
        results = []
        
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        
        return results
    
    def mark_as_embedded(self, provider, id):
        """Mark a case study as having been embedded"""
        cursor = self.conn.cursor()
        cursor.execute('''
        UPDATE case_studies SET is_embedded = 1 WHERE provider = ? AND id = ?
        ''', (provider, id))
        self.conn.commit()
    
    def link_exists(self, provider, link):
        """Check if a link already exists in the database"""
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT COUNT(*) FROM case_studies WHERE provider = ? AND link = ?
        ''', (provider, link))
        count = cursor.fetchone()[0]
        return count > 0
    
    def get_last_id(self, provider):
        """Get the last ID used for a specific provider"""
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT MAX(id) FROM case_studies WHERE provider = ?
        ''', (provider,))
        result = cursor.fetchone()[0]
        return result if result is not None else 0
    
    def close(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()