# Mock Draft Simulator 2025 - Windows Setup

## Installation

1. **Install Python** (if not already installed)
   - Download from: https://www.python.org/downloads/
   - During installation, check "Add Python to PATH"

2. **Run the application**
   - Double-click `run_windows.bat`
   - The script will automatically create a virtual environment on first run

## Syncing with WSL

### From WSL to Windows:
```bash
./sync_to_windows.sh
```

### From Windows to WSL (run in WSL):
```bash
./sync_from_windows.sh
```

## Manual Setup (if batch file doesn't work)

1. Open Command Prompt in the project directory
2. Create virtual environment:
   ```cmd
   python -m venv venv_windows
   ```
3. Activate virtual environment:
   ```cmd
   venv_windows\Scripts\activate
   ```
4. Run the application:
   ```cmd
   python main.py
   ```

## Notes

- The application uses tkinter, which comes built-in with Python on Windows
- Virtual environments are kept separate (venv for Linux, venv_windows for Windows)
- All source code is cross-platform compatible