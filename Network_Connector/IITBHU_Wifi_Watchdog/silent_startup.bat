@echo off
cd /d "%~dp0"
:: Use the custom named executable to run completely silently in the background
start "" .venv\Scripts\IITBHU_Watchdog.exe main.py
