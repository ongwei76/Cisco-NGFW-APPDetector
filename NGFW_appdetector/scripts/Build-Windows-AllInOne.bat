@echo off
setlocal EnableExtensions

set VERSION=%~1
if "%VERSION%"=="" set VERSION=1.2.0

set MIN_PY=%~2
if "%MIN_PY%"=="" set MIN_PY=3.11

echo ============================================
echo NGFW App Detector - All-in-One Builder
echo ============================================
echo Version: %VERSION%
echo Min Python: %MIN_PY%
echo ============================================

cd /d "%~dp0.."
if errorlevel 1 (
  echo [ERROR] Failed to switch to project root.
  exit /b 1
)

echo [1/3] Build EXE...
powershell -ExecutionPolicy Bypass -File .\scripts\build-windows.ps1 -Clean -MinPythonVersion %MIN_PY%
if errorlevel 1 goto :fail
if not exist ".\dist\ngfw-appdetector\ngfw-appdetector.exe" (
  echo [ERROR] EXE not found after build step.
  goto :fail
)

echo [2/3] Package portable ZIP...
powershell -ExecutionPolicy Bypass -File .\scripts\package-windows-portable.ps1 -Version %VERSION%
if errorlevel 1 goto :fail

echo [3/3] Generate SHA256...
powershell -ExecutionPolicy Bypass -Command "$p = Resolve-Path .\release\ngfw-appdetector-windows-portable-%VERSION%.zip; Get-FileHash $p -Algorithm SHA256 | Format-List"
if errorlevel 1 goto :fail

echo.
echo [OK] All done.
echo ZIP: release\ngfw-appdetector-windows-portable-%VERSION%.zip
echo.
pause
exit /b 0

:fail
echo.
echo [ERROR] Process failed. Check messages above.
echo.
pause
exit /b 1
