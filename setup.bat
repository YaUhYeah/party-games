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

REM Remove existing virtual environment if it exists
if exist venv (
    echo Removing existing virtual environment...
    rmdir /s /q venv
)

REM Create virtual environment
echo Creating virtual environment...
python -m pip install --user virtualenv
python -m venv venv

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip in virtual environment
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install wheel and setuptools first
echo Installing wheel and setuptools...
python -m pip install wheel setuptools

REM Install requirements one by one to better handle errors
echo Installing requirements...
echo Installing FastAPI...
python -m pip install fastapi
echo Installing Uvicorn...
python -m pip install uvicorn
echo Installing Socket.IO...
python -m pip install python-socketio
echo Installing Multipart...
python -m pip install python-multipart
echo Installing Pillow...
python -m pip install Pillow
echo Installing QR Code...
python -m pip install qrcode
echo Installing SQLAlchemy...
python -m pip install sqlalchemy
echo Installing aiosqlite...
python -m pip install aiosqlite
echo Installing python-jose...
python -m pip install "python-jose[cryptography]"
echo Installing passlib...
python -m pip install "passlib[bcrypt]"

REM Create necessary directories
echo Creating necessary directories...
mkdir server\static 2>nul
mkdir server\static\music 2>nul
mkdir server\static\profiles 2>nul

echo.
echo Setup complete! To start the server:
echo 1. Activate the virtual environment: venv\Scripts\activate
echo 2. Start the server: python server\main.py
echo 3. Open http://localhost:8000 in your browser
echo.
echo If you encounter any errors, try running these commands manually:
echo python -m pip install --upgrade pip
echo python -m pip install -r server\requirements.txt
echo.

pause