@echo off
echo Running Mock Draft Simulator Tests...
echo.

REM Check if pytest is installed
python -m pytest --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: pytest is not installed.
    echo Please run: pip install -r requirements.txt
    exit /b 1
)

REM Run all tests with verbose output
echo Running all tests...
python -m pytest tests/ -v --tb=short

REM Check if tests passed
if %errorlevel% equ 0 (
    echo.
    echo All tests passed!
) else (
    echo.
    echo Some tests failed. Please check the output above.
)

echo.
pause