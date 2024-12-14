@echo off
echo Setting up Party Games...

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed. Please install Python 3.7+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

REM Create virtual environment
echo Creating virtual environment...
python -m pip install --user virtualenv
python -m venv venv

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install requirements
echo Installing requirements...
python -m pip install -r server\requirements.txt

REM Create necessary directories
echo Creating necessary directories...
mkdir server\static\music 2>nul

echo Setup complete! To start the server:
echo 1. Activate the virtual environment: venv\Scripts\activate
echo 2. Start the server: python server\main.py
echo 3. Open http://localhost:8000 in your browser

pause