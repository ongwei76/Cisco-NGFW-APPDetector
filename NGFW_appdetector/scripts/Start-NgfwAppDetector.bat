@echo off
setlocal

set SCRIPT_DIR=%~dp0
set ROOT_DIR=%SCRIPT_DIR%..
set EXE=
if exist "%SCRIPT_DIR%ngfw-appdetector\ngfw-appdetector.exe" set EXE=%SCRIPT_DIR%ngfw-appdetector\ngfw-appdetector.exe
if "%EXE%"=="" if exist "%ROOT_DIR%\dist\ngfw-appdetector\ngfw-appdetector.exe" set EXE=%ROOT_DIR%\dist\ngfw-appdetector\ngfw-appdetector.exe
set LOG_DIR=%SCRIPT_DIR%logs
set LOG_FILE=%LOG_DIR%\ngfw-appdetector-web.log
set URL=http://127.0.0.1:8765

if not exist "%EXE%" (
  echo [ERROR] Executable not found: %EXE%
  echo Build first: powershell -ExecutionPolicy Bypass -File "%ROOT_DIR%\scripts\build-windows.ps1" -Clean
  exit /b 1
)

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

echo Starting NGFW App Detector on %URL%
echo Logs: %LOG_FILE%
start "NGFW App Detector" "%EXE%" serve --no-browser --host 127.0.0.1 --port 8765 %* > "%LOG_FILE%" 2>&1

timeout /t 2 /nobreak >nul
start "" "%URL%"

echo Done. If the page does not open, browse to %URL%
