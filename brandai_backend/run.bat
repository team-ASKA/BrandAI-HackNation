@echo off
REM BrandAI - Backend Server Startup Script (Windows)
echo Starting BrandAI Backend Server...
echo.

REM Check if .env exists
if not exist .env (
    echo Warning: .env file not found!
    echo Please copy .env.example to .env and add your API keys.
    echo.
    echo The application will run with mock data if API keys are not set.
    echo.
)

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.10+ from https://www.python.org/
    pause
    exit /b 1
)

REM Check if dependencies are installed
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo Error: Failed to install dependencies
        pause
        exit /b 1
    )
)

REM Start the server
echo Starting server on http://localhost:8000
echo Press Ctrl+C to stop the server
echo.
python main.py

pause


