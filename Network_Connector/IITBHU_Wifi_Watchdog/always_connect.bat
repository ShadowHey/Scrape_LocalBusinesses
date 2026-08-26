@echo off
cd /d "%~dp0"

echo ==================================================
echo IIT(BHU) Wi-Fi Watchdog - Auto-Connect Setup
echo ==================================================
echo.

echo [1/2] Creating Windows Startup Shortcut...
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT_PATH=%STARTUP_FOLDER%\Wifi_Watchdog.lnk"
set "VBS_SCRIPT=%TEMP%\CreateShortcut.vbs"

echo Set oWS = WScript.CreateObject("WScript.Shell") > "%VBS_SCRIPT%"
echo sLinkFile = "%SHORTCUT_PATH%" >> "%VBS_SCRIPT%"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%VBS_SCRIPT%"
echo oLink.TargetPath = "%~dp0silent_startup.bat" >> "%VBS_SCRIPT%"
echo oLink.WorkingDirectory = "%~dp0" >> "%VBS_SCRIPT%"
echo oLink.Description = "IIT(BHU) Wi-Fi Watchdog" >> "%VBS_SCRIPT%"
echo oLink.WindowStyle = 7 >> "%VBS_SCRIPT%"
echo oLink.Save >> "%VBS_SCRIPT%"

cscript /nologo "%VBS_SCRIPT%"
del "%VBS_SCRIPT%"

echo [2/2] Starting the Watchdog right now...
start "" silent_startup.bat

echo.
echo ==================================================
echo Setup Complete! 
echo The Watchdog is now running in the background.
echo It will also automatically start every time you 
echo turn on your laptop.
echo.
echo Process Name in Task Manager: IITBHU_Watchdog.exe
echo ==================================================
pause
