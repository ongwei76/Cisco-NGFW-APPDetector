@echo off
setlocal

for /f "tokens=2" %%P in ('tasklist /FI "IMAGENAME eq ngfw-appdetector.exe" /FO LIST ^| find "PID:"') do (
  taskkill /PID %%P /F >nul 2>&1
)

echo Stopped ngfw-appdetector.exe (if it was running).
