#!/bin/bash

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python3 is not installed. Installing..."
    if command -v apt &> /dev/null; then
        # Debian/Ubuntu
        sudo apt update
        sudo apt install -y python3 python3-pip
    elif command -v yum &> /dev/null; then
        # CentOS/RHEL
        sudo yum install -y python3 python3-pip
    elif command -v brew &> /dev/null; then
        # macOS
        brew install python3
    else
        echo "Could not install Python. Please install Python 3.7+ manually."
        exit 1
    fi
fi

# Create virtual environment
echo "Creating virtual environment..."
python3 -m pip install --user virtualenv
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "Installing requirements..."
python3 -m pip install -r server/requirements.txt

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p server/static/music
mkdir -p server/static/profiles

echo "Setup complete! To start the server:"
echo "1. Activate the virtual environment: source venv/bin/activate"
echo "2. Start the server: python3 server/main.py"
echo "3. Open http://localhost:8000 in your browser"