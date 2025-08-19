@echo off
echo ========================================
echo Building Mock Draft Simulator 2025 EXE
echo Simple Build Method
echo ========================================
echo.

REM Check if pyinstaller is installed
python -m pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo PyInstaller not found. Installing...
    python -m pip install pyinstaller
    echo.
)

REM Clean previous builds
echo Cleaning previous builds...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
echo.

REM Build the executable with all options in command line
echo Building executable...
pyinstaller --onefile ^
    --windowed ^
    --name "MockDraftSim2025" ^
    --icon "assets/app_icon.ico" ^
    --add-data "src;src" ^
    --add-data "data;data" ^
    --add-data "assets;assets" ^
    --add-data "config;config" ^
    --add-data "web_static;web_static" ^
    --add-data "web_templates;web_templates" ^
    --add-data "*.md;." ^
    --hidden-import "PIL._tkinter_finder" ^
    --hidden-import "requests" ^
    main.py

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo Build successful!
    echo Executable created: dist\MockDraftSim2025.exe
    echo ========================================
    echo.
    echo You can now:
    echo 1. Navigate to the 'dist' folder
    echo 2. Right-click MockDraftSim2025.exe
    echo 3. Select "Pin to taskbar" or "Create shortcut"
    echo.
    echo The exe file includes all dependencies and data files!
) else (
    echo.
    echo ========================================
    echo Build failed! Check the error messages above.
    echo ========================================
)

echo.
pause