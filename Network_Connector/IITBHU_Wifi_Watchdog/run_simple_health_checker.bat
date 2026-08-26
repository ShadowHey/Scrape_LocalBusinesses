@echo off
cd /d "%~dp0"

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Starting simple health checker...
python simple_health_checker.py

pause
