@echo off
echo =======================================================
echo Starting ModelFinder Application v2.5...
echo =======================================================

REM Check Python environment
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Error: Python not found. Please make sure Python 3.8 or higher is installed and added to PATH.
    pause
    exit /b 1
)

echo Python found. Checking version...
python --version
echo.

echo Starting backend server...
echo Creating logs directory if it doesn't exist
if not exist ModelFinderV2_5\logs mkdir ModelFinderV2_5\logs

echo Installing dependencies and starting API server...
start cmd /k "cd ModelFinderV2_5 && python -m pip install -r requirements.txt && python api_server.py"

echo Waiting for backend to initialize (5 seconds)...
timeout /t 5 /nobreak

echo Starting frontend application...

start "" "frontend\build\windows\x64\runner\Debug\model_finder_flutter.exe"
echo =======================================================
echo ModelFinder is now running!
echo Backend log location: ModelFinderV2_5\logs\
echo Results location: ModelFinderV2_5\results\
echo =======================================================
echo Close this window to stop the application.
pause 