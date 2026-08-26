@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo ==================================================
echo IIT(BHU) Wi-Fi Watchdog - Installation Setup
echo ==================================================
echo.

echo [1/3] Setting up credentials...
if not exist .env (
    copy .env.example .env >nul
)

echo (Leave blank and press Enter if you do not want to change the existing value)
set "USER_INPUT="
set "PASS_INPUT="
set /p "USER_INPUT=Enter your IIT(BHU) Username: "
set /p "PASS_INPUT=Enter your IIT(BHU) Password: "

if not "!USER_INPUT!"=="" (
    powershell -Command "(Get-Content .env) -replace '^IITBHU_USERNAME=.*', 'IITBHU_USERNAME=!USER_INPUT!' | Set-Content .env"
)
if not "!PASS_INPUT!"=="" (
    powershell -Command "(Get-Content .env) -replace '^IITBHU_PASSWORD=.*', 'IITBHU_PASSWORD=!PASS_INPUT!' | Set-Content .env"
)

if not exist .venv (
    echo [2/3] Setting up Python virtual environment...
    python -m venv .venv
) else (
    echo [2/3] Python virtual environment already exists.
)

echo [3/3] Installing dependencies...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul
pip install -r requirements.txt >nul
python -m playwright install chromium >nul

:: Create a custom named executable so it shows up cleanly in Task Manager
echo Naming the background process...
copy /y .venv\Scripts\pythonw.exe .venv\Scripts\IITBHU_Watchdog.exe >nul

echo.
echo ==================================================
echo Installation Complete! 
echo.
echo The software is ready. To make it run automatically 
echo in the background, double-click: always_connect.bat
echo ==================================================
pause
