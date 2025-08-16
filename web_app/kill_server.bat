@echo off
echo Killing any Python processes using port 8080...
echo.

REM Find and kill Python processes using port 8080
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8080') do (
    echo Killing process ID: %%a
    taskkill /F /PID %%a 2>nul
)

echo.
echo Port 8080 should now be free.
echo You can now run run_windows.bat again.
echo.
pause