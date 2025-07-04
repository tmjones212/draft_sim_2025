@echo off
echo Running Mock Draft Simulator Tests with Coverage...
echo.

REM Check if pytest and coverage are installed
python -m pytest --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: pytest is not installed.
    echo Please run: pip install -r requirements.txt
    exit /b 1
)

REM Install coverage if needed
pip show pytest-cov >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing pytest-cov...
    pip install pytest-cov
)

REM Run tests with coverage
echo Running tests with coverage report...
python -m pytest tests/ --cov=src --cov-report=html --cov-report=term -v

REM Open coverage report
if exist htmlcov\index.html (
    echo.
    echo Opening coverage report in browser...
    start htmlcov\index.html
)

echo.
pause