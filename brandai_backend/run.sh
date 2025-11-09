#!/bin/bash
# BrandAI - Backend Server Startup Script (Linux/Mac)

echo "Starting BrandAI Backend Server..."
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "Warning: .env file not found!"
    echo "Please copy .env.example to .env and add your API keys."
    echo ""
    echo "The application will run with mock data if API keys are not set."
    echo ""
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "Error: Python is not installed"
    echo "Please install Python 3.10+ from https://www.python.org/"
    exit 1
fi

# Use python3 if available, otherwise python
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

# Check if dependencies are installed
$PYTHON_CMD -c "import fastapi" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing dependencies..."
    $PYTHON_CMD -m pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "Error: Failed to install dependencies"
        exit 1
    fi
fi

# Start the server
echo "Starting server on http://localhost:8000"
echo "Press Ctrl+C to stop the server"
echo ""
$PYTHON_CMD main.py


