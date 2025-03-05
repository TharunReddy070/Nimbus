FROM python:3.9-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    libgconf-2-4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browser
RUN pip install playwright && python -m playwright install chromium

# Copy the rest of the application
COPY . .

# Create necessary directories
RUN mkdir -p AWS/PDF AWS/TXT GCP/PDF GCP/TXT backup/aws backup/gcp database logs

# Ensure log files exist and are writable
RUN touch logs/aws_scraper.log logs/gcp_scraper.log logs/scheduler.log \
    && chmod 666 logs/aws_scraper.log logs/gcp_scraper.log logs/scheduler.log

# Expose the port the app runs on
EXPOSE 8080

# Command to run the application
CMD ["python", "api.py"] 