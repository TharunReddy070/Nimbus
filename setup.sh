#!/bin/bash

# Cloud Case Study Scraper Setup Script

echo "Setting up Cloud Case Study Scraper..."

# Create necessary directories
echo "Creating directories..."
mkdir -p AWS/PDF AWS/TXT GCP/PDF GCP/TXT backup/aws backup/gcp database logs

# Create empty log files
echo "Creating log files..."
touch logs/aws_scraper.log logs/gcp_scraper.log logs/scheduler.log

# Set permissions
echo "Setting permissions..."
chmod 666 logs/aws_scraper.log logs/gcp_scraper.log logs/scheduler.log

# Check if Python is installed
if command -v python3 &>/dev/null; then
    echo "Python is installed."
    
    # Check if pip is installed
    if command -v pip3 &>/dev/null; then
        echo "Installing dependencies..."
        pip3 install -r requirements.txt
        
        # Install Playwright browser
        echo "Installing Playwright browser..."
        python3 -m playwright install chromium
    else
        echo "pip3 is not installed. Please install pip and run 'pip install -r requirements.txt'."
    fi
else
    echo "Python is not installed. Please install Python 3.9 or later."
fi

echo "Setup complete! You can now run the application with:"
echo "  - For local Python: python api.py"
echo "  - For Docker: docker-compose up --build" 