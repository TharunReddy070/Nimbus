import os
import json
import uuid
import asyncio
import logging
from datetime import datetime
from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, validator
from typing import Optional, List, Dict
import psycopg2
from psycopg2.extras import RealDictCursor
from openai import AsyncOpenAI
from dotenv import load_dotenv
import uvicorn
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("rag_api.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants
NEON_DATABASE_URL = os.getenv("NEON_DATABASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL = "text-embedding-3-small"
LLM_MODEL = "gpt-4o-mini"
VECTOR_SIMILARITY_THRESHOLD = 0.0
VECTOR_SIMILARITY_LIMIT = 3

# Initialize FastAPI app
app = FastAPI(title="RAG API for Cloud Case Studies")

# Configure CORS to allow requests from the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request and response validation
class QueryRequest(BaseModel):
    user_query: str
    session_id: str = "first_time"
    
    @validator('user_query')
    def validate_user_query(cls, v):
        if not v or not v.strip():
            raise ValueError("User query cannot be empty")
        return v.strip()

class QueryResponse(BaseModel):
    session_id: str
    response: str
    citation_array: List[Dict]

# Initialize OpenAI client
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Database connection function
def get_db_connection():
    try:
        conn = psycopg2.connect(NEON_DATABASE_URL)
        conn.autocommit = False  # Use explicit transactions
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        return conn, cursor
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise HTTPException(status_code=500, detail="Database connection error")

# Function to generate embedding for query
async def generate_embedding(text: str) -> List[float]:

    # STREAMING LOG MESSAGE : <MESSAGE>"Generating embedding for the RAG query"</MESSAGE>

    try:
        response = await client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        raise HTTPException(status_code=500, detail="Error generating embedding")

# Function to perform vector search in the database
async def vector_search(query_embedding: List[float], cloud_provider: str, threshold: float = VECTOR_SIMILARITY_THRESHOLD, limit: int = VECTOR_SIMILARITY_LIMIT) -> List[Dict]:

    # STREAMING LOG MESSAGE : <MESSAGE>"Retrieving relevant case studies"</MESSAGE>

    try:
        conn, cursor = get_db_connection()
        results = []
        
        # Determine which tables to query based on cloud provider
        if cloud_provider.lower() == "aws":
            tables = ["case_studies"]
        elif cloud_provider.lower() == "gcp":
            tables = ["gcp_case_studies"]
        else:
            # For other providers, query both tables
            tables = ["case_studies", "gcp_case_studies"]
            # Don't split the limit - get the full limit from each table
            # We'll sort and limit the combined results later
        
        for table_name in tables:
            # Check if the table exists
            cursor.execute(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = '{table_name}'
                );
            """)
            table_exists = cursor.fetchone()["exists"]
            
            if not table_exists:
                logger.warning(f"{table_name} not found in database")
                continue
            
            # Ensure pgvector extension is installed
            try:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                conn.commit()
            except Exception as e:
                logger.error(f"Error installing pgvector extension: {e}")
                continue
            
            # Perform vector similarity search
            query = f"""
                SELECT 
                    id, case_id, content, link, company_name, region, 
                    services_used, outcomes, summary, year, industry,
                    1 - (embedding <=> %s::vector) as similarity
                FROM {table_name}
                WHERE 1 - (embedding <=> %s::vector) > %s
                ORDER BY similarity DESC
                LIMIT %s;
            """
            
            # Convert embedding to PostgreSQL array format
            embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
            
            cursor.execute(query, (embedding_str, embedding_str, threshold, limit))
            table_results = cursor.fetchall()
            results.extend([dict(r) for r in table_results])
        
        conn.close()

        
        # Sort combined results by similarity if querying both tables
        if len(tables) > 1:
            # Take only the top 'limit' results after sorting all results by similarity
            results = sorted(results, key=lambda x: x['similarity'], reverse=True)[:limit]
        
        return results
        
    except Exception as e:
        logger.error(f"Error in vector search: {e}")
        if 'conn' in locals() and conn:
            conn.close()
        return []

# Function to create or update session
async def manage_session(session_id: str, user_query: str) -> str:
    try:
        conn, cursor = get_db_connection()
        
        # Check if we need to create a new session
        if session_id == "first_time":
            new_session_id = str(uuid.uuid4())
            
            # Create conversation_history table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversation_history (
                    id SERIAL PRIMARY KEY,
                    role VARCHAR(10) NOT NULL,
                    content TEXT NOT NULL,
                    conv_summary TEXT,
                    session_id UUID NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()
            
            logger.info(f"Created new session with ID: {new_session_id}")
            
            # Return the new session ID
            conn.close()
            return new_session_id
        
        # Validate existing session ID
        try:
            # Try to parse the session_id as a UUID to validate it
            uuid_obj = uuid.UUID(session_id)
            
            # Check if session exists in the database
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM conversation_history 
                WHERE session_id = %s
            """, (str(uuid_obj),))
            
            result = cursor.fetchone()
            
            if not result or result["count"] == 0:
                # Session doesn't exist in the database, create a new one
                logger.info(f"Session ID {session_id} not found in database, creating new session")
                new_session_id = str(uuid.uuid4())
                conn.close()
                return new_session_id
            
            # Session exists, return the existing session ID
            logger.info(f"Using existing session with ID: {session_id}")
            conn.close()
            return session_id
            
        except ValueError:
            # Invalid UUID format, create a new one
            logger.warning(f"Invalid session ID format: {session_id}, creating new session")
            new_session_id = str(uuid.uuid4())
            conn.close()
            return new_session_id
            
    except Exception as e:
        logger.error(f"Error managing session: {e}")
        if 'conn' in locals() and conn:
            conn.close()
        return str(uuid.uuid4())  # Return a new session ID as fallback

# Function to get conversation summary
async def get_conversation_summary(session_id: str) -> str:

    # STREAMING LOG MESSAGE : <MESSAGE>"Understanding the context of the conversation"</MESSAGE> 
    # STREAMING LOG MESSAGE IF NO SESSION_IF = "first_time" : <MESSAGE>"No previous conversation history found"</MESSAGE>

    try:
        conn, cursor = get_db_connection()
        
        # Get the most recent conversation summary
        cursor.execute("""
            SELECT conv_summary 
            FROM conversation_history 
            WHERE session_id = %s 
            ORDER BY created_at DESC 
            LIMIT 1
        """, (session_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result and result["conv_summary"]:
            return result["conv_summary"]
        
        return ""
    except Exception as e:
        logger.error(f"Error getting conversation summary: {e}")
        if 'conn' in locals() and conn:
            conn.close()
        return ""

# Function to store conversation history in background
async def store_conversation(role: str, content: str, conv_summary: str, session_id: str):
    try:
        conn, cursor = get_db_connection()
        
        cursor.execute("""
            INSERT INTO conversation_history (role, content, conv_summary, session_id)
            VALUES (%s, %s, %s, %s)
        """, (role, content, conv_summary, session_id))
        
        conn.commit()
        conn.close()
        logger.info(f"Stored conversation entry for session {session_id}")
    except Exception as e:
        logger.error(f"Error storing conversation: {e}")
        if 'conn' in locals() and conn:
            conn.close()

# LLM call for query processing
async def process_query_with_llm(user_query: str, conv_summary: str) -> Dict:

    # STREAMING LOG MESSAGE : <MESSAGE>"Processing the user query, rewriting the query and determining the cloud provider"</MESSAGE>

    json_schema = {
  "name": "json_schema",
  "schema": {
    "type": "object",
    "properties": {
      "rag_query": {
        "type": "string",
        "description": "Optimized query for vector search"
      },
      "rewritten_query": {
        "type": "string",
        "description": "Rewritten user query with context"
      },
      "cloud_provider": {
        "type": "string",
        "enum": [
          "aws",
          "gcp",
          "others"
        ],
        "description": "Cloud provider mentioned in the query"
      }
    },
    "required": [
      "rag_query",
      "rewritten_query",
      "cloud_provider"
    ],
    "additionalProperties": False
  },
  "strict": True
}
    
    # Prompt template
    prompt = f"""
    ### Task
    You are an AI assistant for cloud computing. Process the user's query and determine the best search parameters.
    
    ### Conversation Context
    {conv_summary if conv_summary else "No prior conversation."}
    
    ### Current User Query
    {user_query}
    
    ### Instructions
    1. Create an optimized RAG query for searching a vector database of cloud case studies.
    2. Rewrite the user query with any contextual information from previous conversation.
    3. Determine which cloud provider is most relevant (AWS, GCP, or others).
    
    Return a structured JSON response containing the rag_query, rewritten_query, and cloud_provider fields.
    """
    
    try:
        response = await client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={
                "type": "json_schema",
                "json_schema": json_schema
            }
        )
        
        # Parse the JSON response
        content = response.choices[0].message.content
        try:
            result = json.loads(content)
            logger.info(f"Successfully parsed LLM response: {str(result)[:100]}...")
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Raw response: {content}")
            return {
                "rag_query": user_query,
                "rewritten_query": user_query,
                "cloud_provider": "aws"
            }
    except Exception as e:
        logger.error(f"Error in LLM process_query: {e}")
        # Return default values in case of error
        return {
            "rag_query": user_query,
            "rewritten_query": user_query,
            "cloud_provider": "aws"  # Default to AWS
        }

# LLM call for generating the answer
async def generate_answer_with_llm(rewritten_query: str, retrieved_content: List[Dict]) -> str:

    # STREAMING LOG MESSAGE : <MESSAGE>"Generating the final answer"</MESSAGE>

    # Prepare content from retrieved documents
    content_text = ""
    for i, doc in enumerate(retrieved_content):
        content_text += f"\n--- Document {i+1} ---\n"
        content_text += f"Case Study: {doc.get('company_name', 'Unknown')}\n"
        content_text += f"Industry: {doc.get('industry', 'Unknown')}\n"
        content_text += f"Summary: {doc.get('summary', '')}\n"
        content_text += f"Content: {doc.get('content', '')}...\n"
    
    if not content_text:
        content_text = "No relevant case studies found."
    
    # Prompt template
    prompt = f"""
    ### Task
    You are an AI assistant for cloud computing. Answer the user's query based on the retrieved case studies.
    
    ### User Query
    {rewritten_query}
    
    ### Retrieved Case Studies
    {content_text}
    
    ### Instructions
    1. Answer the user's question based on the provided case studies.
    2. If the case studies don't contain relevant information, provide a general answer based on your knowledge.
    3. Always cite specific companies or services mentioned in your answer.
    4. Keep your answer concise but informative.
    """
    
    try:
        response = await client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error in LLM generate_answer: {e}")
        return "I'm sorry, I couldn't generate an answer at this time. Please try again later."

# LLM call for updating the conversation summary
async def update_conversation_summary(user_query: str, answer: str, current_summary: str) -> str:
    # JSON schema for structured output
    json_schema = {
  "name": "my_schema",
  "schema": {
    "type": "object",
    "properties": {
      "updated_summary": {
        "type": "string",
        "description": "Updated summary of the conversation history"
      }
    },
    "required": [
      "updated_summary"
    ],
    "additionalProperties": False
  },
        "strict": True
    }
    
    # Prompt template
    prompt = f"""
    ### Task
    You are a conversation summarizer. Update the conversation summary with the latest interaction.
    
    ### Current Summary
    {current_summary if current_summary else "No prior conversation."}
    
    ### Latest Interaction
    User: {user_query}
    
    Assistant: {answer}
    
    ### Instructions
    1. Create a concise summary that captures the key points of the entire conversation so far.
    2. Include important context, questions, and information from both the user and assistant.
    3. Focus on maintaining information that might be relevant for future queries.
    4. Keep the summary under 500 words.
    
    Return a structured JSON response containing only the updated_summary field.
    """
    
    try:
        response = await client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={
                "type": "json_schema",
                "json_schema": json_schema
            }
        )
        
        # Parse the JSON response
        content = response.choices[0].message.content
        try:
            result = json.loads(content)
            if "updated_summary" in result:
                return result["updated_summary"]
            else:
                logger.warning(f"Missing updated_summary in response: {result}")
                return current_summary or ""
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM summary response as JSON: {e}")
            logger.error(f"Raw response: {content}")
            # In case of error, concatenate the new interaction to current summary
            new_interaction = f"\nUser: {user_query}\nAssistant: {answer}"
            return (current_summary + new_interaction) if current_summary else new_interaction
    except Exception as e:
        logger.error(f"Error in LLM update_summary: {e}")
        # In case of error, concatenate the new interaction to current summary
        new_interaction = f"\nUser: {user_query}\nAssistant: {answer}"
        return (current_summary + new_interaction) if current_summary else new_interaction

# Background task to update conversation history
async def update_conversation_history(user_query: str, answer: str, session_id: str, conv_summary: str):
    # Get current conversation summary
    current_summary = await get_conversation_summary(session_id)
    
    # Update the summary with the new interaction
    updated_summary = await update_conversation_summary(user_query, answer, current_summary)
    
    # Store user message
    await store_conversation("user", user_query, updated_summary, session_id)
    
    # Store bot message
    await store_conversation("bot", answer, updated_summary, session_id)
    
    logger.info(f"Updated conversation history for session {session_id}")

# Helper function to safely encode JSON while preserving markdown content
def safe_json_encode(obj):
    """Safely encode an object to JSON string, handling potential encoding issues."""
    try:
        return json.dumps(obj)
    except Exception as e:
        logger.error(f"JSON encoding error: {e}")
        # Try a more robust approach
        try:
            # Use a more tolerant JSON encoder
            import json as standard_json
            return standard_json.dumps(obj, ensure_ascii=True, default=str)
        except Exception as e2:
            logger.error(f"Fallback JSON encoding also failed: {e2}")
            # Last resort: return a simplified error object
            return json.dumps({"type": "error", "message": "Failed to encode response"})

# Function to ensure JSON-safe strings while preserving markdown
def ensure_json_safe(text):
    """Make text safe for JSON encoding while preserving markdown formatting."""
    if not text:
        return ""
    
    # Replace problematic control characters that break JSON
    # but preserve newlines and other markdown-relevant characters
    replacements = {
        '\u0000': '',      # Null byte
        '\u001F': '',      # Unit separator
        '\u000B': '\n',    # Vertical tab to newline
        '\u000C': '\n',    # Form feed to newline
        '\r\n': '\n',      # Normalize line endings
        '\r': '\n',        # Carriage return to newline
    }
    
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    
    # Ensure unicode characters are properly handled
    return text

# Create a processing steps generator to stream the backend processing
async def processing_stream(request: QueryRequest):
    """Generate processing steps as a stream to the frontend."""
    try:
        # Log the received query
        logger.info(f"Received query request: {request.user_query[:100]}...")

        # Step 1: Manage session
        session_id = await manage_session(request.session_id, request.user_query)
        logger.info(f"Using session ID: {session_id}")
        
        # Send message: Understanding context
        if request.session_id == "first_time":
            yield safe_json_encode({"type": "processing_step", "message": "No previous conversation history found"}) + "\n"
        
        yield safe_json_encode({"type": "processing_step", "message": "Understanding the context of the conversation"}) + "\n"
        
        # Step 2: Get conversation summary
        conv_summary = await get_conversation_summary(session_id)
        
        # Step 3: Process query with LLM
        yield safe_json_encode({"type": "processing_step", "message": "Processing the user query, rewriting the query and determining the cloud provider"}) + "\n"
        query_processing = await process_query_with_llm(request.user_query, conv_summary)
        
        # Validate returned structure matches expected schema
        if not isinstance(query_processing, dict) or not all(k in query_processing for k in ["rag_query", "rewritten_query", "cloud_provider"]):
            logger.error(f"Invalid query processing result: {query_processing}")
            # Fallback to defaults
            rag_query = request.user_query
            rewritten_query = request.user_query
            cloud_provider = "aws"
        else:
            rag_query = query_processing["rag_query"]
            rewritten_query = query_processing["rewritten_query"]
            cloud_provider = query_processing["cloud_provider"]
            
            logger.info(f"RAG query: {rag_query[:100]}...")
            logger.info(f"Cloud provider: {cloud_provider}")
            
            logger.info("No Fallback in query processing")
        
        # Step 4: Generate embedding for the RAG query
        yield safe_json_encode({"type": "processing_step", "message": "Generating embedding for the RAG query"}) + "\n"
        query_embedding = await generate_embedding(rag_query)
        
        # Step 5: Search vector database
        yield safe_json_encode({"type": "processing_step", "message": "Retrieving relevant case studies"}) + "\n"
        retrieved_content = await vector_search(query_embedding, cloud_provider)
        logger.info(f"Retrieved {len(retrieved_content)} relevant documents")
        
        # Step 6: Generate answer
        yield safe_json_encode({"type": "processing_step", "message": "Generating the final answer"}) + "\n"
        answer = await generate_answer_with_llm(rewritten_query, retrieved_content)
        
        # Ensure the answer is JSON-safe while preserving markdown
        answer = ensure_json_safe(answer)
        
        # Step 7: Format response with citations
        citation_array = []
        for doc in retrieved_content:
            # Get content and ensure it's JSON-safe while preserving markdown
            company_name = ensure_json_safe(doc.get("company_name", ""))
            content = ensure_json_safe(doc.get("content", ""))
            link = ensure_json_safe(doc.get("link", ""))
            
            # Limit citation content length if extremely long
            MAX_CITATION_LENGTH = 10000  # Adjust as needed - keeping long to preserve markdown
            if len(content) > MAX_CITATION_LENGTH:
                content = content[:MAX_CITATION_LENGTH] + "...\n\n*Content truncated due to length*"
            
            citation = {
                "company_name": company_name,
                "content": content,
                "link": link
            }
            citation_array.append(citation)

        # Step 8: Send the complete response
        final_response = {
            "type": "complete",
            "session_id": session_id,
            "response": answer,
            "citation_array": citation_array
        }
        
        try:
            # Try to encode the full response
            yield safe_json_encode(final_response) + "\n"
        except Exception as json_error:
            logger.error(f"Failed to encode complete response: {json_error}")
            # Fallback: try with limited citations
            try:
                # Create a simplified version with limited citation content
                simplified_citations = []
                for citation in citation_array:
                    simplified_citations.append({
                        "company_name": citation["company_name"],
                        "content": citation["content"][:1000] + "... (truncated)",
                        "link": citation["link"]
                    })
                
                simplified_response = {
                    "type": "complete",
                    "session_id": session_id,
                    "response": answer,
                    "citation_array": simplified_citations
                }
                yield safe_json_encode(simplified_response) + "\n"
            except Exception as fallback_error:
                logger.error(f"Fallback encoding also failed: {fallback_error}")
                # Last resort: send response without citations
                minimal_response = {
                    "type": "complete",
                    "session_id": session_id,
                    "response": answer,
                    "citation_array": []
                }
                yield safe_json_encode(minimal_response) + "\n"
        
        # Step 9: Schedule background task to update conversation history
        # This happens after response is sent back to client
        asyncio.create_task(
            update_conversation_history(
                request.user_query,
                answer,
                session_id,
                conv_summary
            )
        )
        
    except Exception as e:
        logger.error(f"Error in processing stream: {e}", exc_info=True)
        # Send error response
        error_response = {
            "type": "error",
            "message": f"Error processing query: {str(e)}"
        }
        yield safe_json_encode(error_response) + "\n"

@app.post("/query")
async def query(request: QueryRequest):
    """Process user query and return streaming response."""
    logger.info(f"Received query: '{request.user_query}'")
    
    # Return a streaming response
    return StreamingResponse(
        processing_stream(request),
        media_type="application/x-ndjson"
    )

# Successfully running message when I visit home route "/"
@app.get("/")
async def home():
    return {"status": "healthy", "message": "Cloud Case Study RAG API is running successfully!", "timestamp": datetime.now().isoformat()}

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Add appropriate error handling for request models
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors for requests"""
    error_detail = exc.errors()
    error_message = "Invalid request parameters"
    
    # Check if this is a streaming endpoint
    if request.url.path == "/query":
        # For streaming endpoints, return a StreamingResponse
        async def error_stream():
            yield json.dumps({
                "type": "error",
                "message": error_message,
                "detail": error_detail
            }) + "\n"
        
        return StreamingResponse(
            error_stream(),
            media_type="application/x-ndjson"
        )
    else:
        # For regular endpoints, return a JSONResponse
        return JSONResponse(
            status_code=422,
            content={
                "detail": error_detail,
                "message": error_message,
            }
        )

if __name__ == "__main__":
    uvicorn.run("rag:app", host="0.0.0.0", port=8000, reload=True)