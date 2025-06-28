@echo off
echo Starting Mock Draft Simulator 2025...

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH
    echo Please install Python from https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv_windows" (
    echo Creating virtual environment...
    python -m venv venv_windows
)

REM Activate virtual environment
call venv_windows\Scripts\activate

REM Run the application
python main.py

REM Keep window open if there's an error
if errorlevel 1 pause