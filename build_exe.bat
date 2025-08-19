@echo off
echo ========================================
echo Building Mock Draft Simulator 2025 EXE
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
if exist "MockDraftSim2025.exe" del "MockDraftSim2025.exe"
echo.

REM Build the executable
echo Building executable...
pyinstaller mock_draft_sim.spec --noconfirm

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo Build successful!
    echo Executable created: dist\MockDraftSim2025.exe
    echo ========================================
    
    REM Copy exe to root directory for easy access
    if exist "dist\MockDraftSim2025.exe" (
        copy "dist\MockDraftSim2025.exe" "MockDraftSim2025.exe"
        echo.
        echo Executable copied to: MockDraftSim2025.exe
    )
    
    echo.
    echo You can now:
    echo 1. Run MockDraftSim2025.exe directly
    echo 2. Create a shortcut and pin it to your taskbar
    echo 3. Move it to any location you prefer
) else (
    echo.
    echo ========================================
    echo Build failed! Check the error messages above.
    echo ========================================
)

echo.
pause