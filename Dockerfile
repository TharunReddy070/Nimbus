# Use Python 3.9 with Debian Bullseye (more stable apt repositories)
FROM python:3.9-slim-bullseye

# Set working directory
WORKDIR /app

# Install Python dependencies with optimized pip commands
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir psycopg2-binary pandas openai python-dotenv \
    asyncio PyPDF2 aiohttp fastapi uvicorn

# Install only essential system dependencies with optimized apt commands
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    # Clean up in the same layer to reduce image size
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright with minimal browser (only chromium)
RUN pip install playwright && \
    playwright install chromium && \
    rm -rf ~/.cache/ms-playwright/firefox* ~/.cache/ms-playwright/webkit*

# Copy only the required files
COPY aws_main.py .
COPY scrapping/ ./scrapping/
COPY gcp_main.py .
COPY main.py .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Expose port for Cloud Run
EXPOSE 8080

# Run FastAPI server and scraping scripts
# The FastAPI server will handle HTTP requests, while the scraping scripts run in the background
CMD ["sh", "-c", "python aws_main.py & python gcp_main.py & python main.py"]
