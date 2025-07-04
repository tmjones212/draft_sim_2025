@echo off
echo ========================================
echo Running Projections Pipeline
echo ========================================
echo.

echo Step 1: Pulling projections from API...
python pull_projections.py
if errorlevel 1 (
    echo Error pulling projections!
    pause
    exit /b 1
)
echo.

echo Step 2: Aggregating projections...
python aggregate_projections.py
if errorlevel 1 (
    echo Error aggregating projections!
    pause
    exit /b 1
)
echo.

echo Step 3: Calculating fantasy points...
python calculate_projection_fantasy_points.py
if errorlevel 1 (
    echo Error calculating fantasy points!
    pause
    exit /b 1
)
echo.

echo ========================================
echo Projections pipeline completed successfully!
echo ========================================
pause