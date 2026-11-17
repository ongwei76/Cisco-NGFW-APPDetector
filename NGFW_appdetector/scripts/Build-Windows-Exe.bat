@echo off
setlocal EnableExtensions

set MIN_PY=%~1
if "%MIN_PY%"=="" set MIN_PY=3.11

echo ============================================
echo NGFW App Detector - Windows EXE Builder
echo ============================================

cd /d "%~dp0.."
if errorlevel 1 (
  echo [ERROR] Failed to switch to project root.
  exit /b 1
)

echo Building with minimum Python version %MIN_PY% ...
powershell -ExecutionPolicy Bypass -File .\scripts\build-windows.ps1 -Clean -MinPythonVersion %MIN_PY%
if errorlevel 1 goto :fail

echo.
echo [OK] Build complete.
echo Output: dist\ngfw-appdetector\ngfw-appdetector.exe
echo.
pause
exit /b 0

:fail
echo.
echo [ERROR] Build failed. Check messages above.
echo.
pause
exit /b 1
