@echo off
echo Stopping IITBHU Wi-Fi Watchdog...
taskkill /F /IM IITBHU_Watchdog.exe /T
echo Watchdog has been stopped successfully.
pause
