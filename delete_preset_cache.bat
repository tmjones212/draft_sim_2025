@echo off
echo Deleting draft preset cache file...
del /f /q "data\draft_presets.json" 2>nul
if exist "data\draft_presets.json" (
    echo Failed to delete draft_presets.json
) else (
    echo Draft preset cache cleared successfully
)
pause