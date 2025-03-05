@echo off
echo Setting up Cloud Case Study Scraper...

REM Create necessary directories
echo Creating directories...
mkdir AWS\PDF AWS\TXT GCP\PDF GCP\TXT backup\aws backup\gcp database logs 2>nul

REM Create empty log files
echo Creating log files...
type nul > logs\aws_scraper.log
type nul > logs\gcp_scraper.log
type nul > logs\scheduler.log

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo Python is installed.
    
    REM Check if pip is installed
    pip --version >nul 2>&1
    if %errorlevel% equ 0 (
        echo Installing dependencies...
        pip install -r requirements.txt
        
        REM Install Playwright browser
        echo Installing Playwright browser...
        python -m playwright install chromium
    ) else (
        echo pip is not installed. Please install pip and run 'pip install -r requirements.txt'.
    )
) else (
    echo Python is not installed. Please install Python 3.9 or later.
)

echo Setup complete! You can now run the application with:
echo   - For local Python: python api.py
echo   - For Docker: docker-compose up --build

pause 