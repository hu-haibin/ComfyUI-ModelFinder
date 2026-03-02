@echo off
chcp 65001 >nul
REM ===== Model Finder Launcher =====
REM Version: 2.6
REM Contact: WeChat wangdefa4567

echo Starting Model Finder 2.6...

REM Set current directory to script location
cd /d "%~dp0"

REM ===== Check Python =====
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not detected.
    echo Please install Python 3.8+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

REM ===== Check Chrome =====
set "CHROME_FOUND=0"
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" set "CHROME_FOUND=1"
if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set "CHROME_FOUND=1"
if exist "%LocalAppData%\Google\Chrome\Application\chrome.exe" set "CHROME_FOUND=1"

if %CHROME_FOUND% EQU 0 (
    echo [WARNING] Chrome not detected. Installing Chrome...
    winget install Google.Chrome --silent --accept-package-agreements --accept-source-agreements
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to install Chrome automatically.
        echo Please install manually: https://www.google.com/chrome/
        pause
        exit /b 1
    )
    echo Chrome installed successfully.
)

REM ===== Check and install Python dependencies =====
echo Checking dependencies...
python -c "import ttkbootstrap; import pandas; import DrissionPage" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Installing required packages...
    python -m pip install -r requirements.txt
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to install packages. Please check the messages above.
        pause
        exit /b 1
    )
    echo Packages installed successfully.
)

REM ===== Launch the application =====
python run_model_finder.py

pause
