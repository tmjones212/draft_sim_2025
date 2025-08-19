# Building Mock Draft Simulator 2025 as an Executable

## Prerequisites
- Python 3.8 or higher installed
- Windows operating system

## Quick Build Instructions

### Method 1: Using the Build Script (Recommended)
1. Double-click `build_exe_simple.bat`
2. Wait for the build to complete (may take 2-3 minutes)
3. Find your executable in the `dist` folder
4. The file will be named `MockDraftSim2025.exe`

### Method 2: Manual Build
Open Command Prompt or PowerShell in the project directory and run:
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "MockDraftSim2025" --icon "assets/app_icon.ico" main.py
```

## After Building

### Pin to Taskbar
1. Navigate to the `dist` folder
2. Right-click on `MockDraftSim2025.exe`
3. Select "Pin to taskbar"

### Create Desktop Shortcut
1. Right-click on `MockDraftSim2025.exe`
2. Select "Create shortcut"
3. Move the shortcut to your Desktop

### Move to Custom Location
The executable is self-contained and can be moved anywhere:
- Program Files folder
- Desktop
- Custom tools folder
- USB drive (portable)

## Troubleshooting

### Build Fails
- Make sure Python is installed: `python --version`
- Install required packages: `pip install -r requirements.txt`
- Try the alternative build script: `build_exe.bat`

### Executable Won't Run
- Check Windows Defender - it may block the first run
- Right-click the exe and select "Run as administrator" (first time only)
- Make sure you have Visual C++ Redistributables installed

### Missing Data Files
The executable includes all data files, but if you see errors:
- Make sure the build completed successfully
- Try rebuilding with `build_exe.bat` (uses spec file)

## File Size
The executable will be approximately 50-100 MB as it includes:
- Python interpreter
- All dependencies (tkinter, PIL, requests, etc.)
- All data files and assets
- The application code

## Updating the Executable
When you make changes to the code:
1. Run the build script again
2. Replace the old executable with the new one
3. Any shortcuts you created will still work

## Distribution
You can share the `MockDraftSim2025.exe` file with others:
- No Python installation required on their machine
- All dependencies are included
- Just send them the single .exe file

## Advanced Options

### Reduce File Size
Edit `build_exe_simple.bat` and remove the `--onefile` option to create a folder distribution instead of a single file.

### Show Console (for debugging)
Remove the `--windowed` option from the build command to show the console window.

### Custom Icon
Replace `assets/app_icon.ico` with your own icon file before building.