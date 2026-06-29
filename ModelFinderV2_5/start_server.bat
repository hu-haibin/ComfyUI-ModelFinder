@echo off
echo Starting ModelFinder backend server...

REM Check Python environment
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Python not found. Please make sure Python 3.8 or higher is installed and added to PATH.
    pause
    exit /b 1
)

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Start API server
echo Starting API server...
python api_server.py

pause 