FROM python:3.10-slim

WORKDIR /app

COPY rag.py .

RUN pip install --no-cache-dir fastapi uvicorn openai python-dotenv psycopg2-binary pydantic && \
    apt-get update && \
    apt-get install -y --no-install-recommends libpq-dev gcc curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir -p /app/logs && \
    touch /app/rag_api.log && \
    chmod 777 /app/rag_api.log

EXPOSE 8000

ENV OPENAI_API_KEY=""
ENV NEON_DATABASE_URL=""

CMD ["uvicorn", "rag:app", "--host", "0.0.0.0", "--port", "8000"] 