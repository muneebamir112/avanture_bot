@echo off
echo ========================================================
echo  Launching Real Google Chrome with Local Profile
echo  Profile Location: %~dp0chrome_profile
echo  Port: 9222 (for Automation Bot to connect)
echo  Target: https://www.avanture.net/
echo ========================================================

start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%~dp0chrome_profile" https://www.avanture.net/
