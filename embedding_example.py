from db_manager import DatabaseManager
import time
import asyncio

async def process_embeddings(provider=None, batch_size=5):
    """Process embeddings for unembedded case studies"""
    db = DatabaseManager()
    
    # Get unembedded case studies
    unembedded = db.get_unembedded_case_studies(provider, limit=batch_size)
    
    if not unembedded:
        return 0
    
    processed_count = 0
    
    for study in unembedded:
        id = study['id']
        provider = study['provider']
        content = study['content']
        
        # Here you would implement your actual embedding logic
        # For example:
        # embedding = your_embedding_model.embed(content)
        # store_embedding_somewhere(id, embedding)
        
        # Simulate embedding process
        await asyncio.sleep(0.5)
        
        # Update the embedding status in the database
        db.mark_as_embedded(provider, id)
        processed_count += 1
    
    db.close()
    return processed_count

if __name__ == "__main__":
    import sys
    
    # Parse command line arguments
    provider = None
    batch_size = 5
    
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--provider" and i+1 < len(sys.argv):
            provider = sys.argv[i+1]
            i += 2
        elif sys.argv[i] == "--batch-size" and i+1 < len(sys.argv):
            try:
                batch_size = int(sys.argv[i+1])
                i += 2
            except ValueError:
                print(f"Invalid batch size: {sys.argv[i+1]}")
                i += 2
        else:
            i += 1
    
    asyncio.run(process_embeddings(provider, batch_size)) 