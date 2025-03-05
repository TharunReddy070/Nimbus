import os
import logging
from pathlib import Path
from google.cloud import storage
from google.cloud.exceptions import NotFound

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cloud_storage")

class CloudStorage:
    def __init__(self, bucket_name=None):
        """Initialize the cloud storage handler"""
        self.bucket_name = bucket_name or os.environ.get("STORAGE_BUCKET")
        
        if not self.bucket_name:
            logger.warning("No storage bucket specified. Data will not be persisted to cloud storage.")
            self.enabled = False
            return
            
        try:
            self.client = storage.Client()
            self.bucket = self.client.bucket(self.bucket_name)
            
            # Check if bucket exists
            if not self.bucket.exists():
                logger.warning(f"Bucket {self.bucket_name} does not exist. Creating it...")
                self.client.create_bucket(self.bucket_name)
                
            self.enabled = True
            logger.info(f"Cloud Storage initialized with bucket: {self.bucket_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Cloud Storage: {str(e)}")
            self.enabled = False
    
    def sync_to_cloud(self):
        """Sync local directories to cloud storage"""
        if not self.enabled:
            logger.warning("Cloud Storage is not enabled. Skipping sync to cloud.")
            return False
            
        try:
            dirs_to_sync = ['AWS', 'GCP', 'backup', 'database']
            total_files = 0
            
            for dir_name in dirs_to_sync:
                dir_path = Path(dir_name)
                if not dir_path.exists():
                    continue
                    
                for root, _, files in os.walk(dir_path):
                    for file in files:
                        local_path = os.path.join(root, file)
                        blob_path = local_path.replace("\\", "/")  # Normalize path for cloud storage
                        
                        # Skip temporary files
                        if file.startswith('.') or file.endswith('.tmp'):
                            continue
                            
                        blob = self.bucket.blob(blob_path)
                        blob.upload_from_filename(local_path)
                        total_files += 1
            
            logger.info(f"Synced {total_files} files to cloud storage")
            return True
        except Exception as e:
            logger.error(f"Error syncing to cloud: {str(e)}")
            return False
    
    def sync_from_cloud(self):
        """Sync from cloud storage to local directories"""
        if not self.enabled:
            logger.warning("Cloud Storage is not enabled. Skipping sync from cloud.")
            return False
            
        try:
            blobs = self.client.list_blobs(self.bucket_name)
            total_files = 0
            
            for blob in blobs:
                local_path = blob.name
                
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                
                # Download file if it doesn't exist locally or is older
                if not os.path.exists(local_path) or os.path.getmtime(local_path) < blob.updated.timestamp():
                    blob.download_to_filename(local_path)
                    total_files += 1
            
            logger.info(f"Synced {total_files} files from cloud storage")
            return True
        except Exception as e:
            logger.error(f"Error syncing from cloud: {str(e)}")
            return False
    
    def upload_file(self, local_path, blob_path=None):
        """Upload a single file to cloud storage"""
        if not self.enabled:
            return False
            
        try:
            blob_path = blob_path or local_path.replace("\\", "/")
            blob = self.bucket.blob(blob_path)
            blob.upload_from_filename(local_path)
            logger.info(f"Uploaded {local_path} to {blob_path}")
            return True
        except Exception as e:
            logger.error(f"Error uploading file {local_path}: {str(e)}")
            return False
    
    def download_file(self, blob_path, local_path=None):
        """Download a single file from cloud storage"""
        if not self.enabled:
            return False
            
        try:
            local_path = local_path or blob_path
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            blob = self.bucket.blob(blob_path)
            blob.download_to_filename(local_path)
            logger.info(f"Downloaded {blob_path} to {local_path}")
            return True
        except NotFound:
            logger.warning(f"File {blob_path} not found in cloud storage")
            return False
        except Exception as e:
            logger.error(f"Error downloading file {blob_path}: {str(e)}")
            return False 