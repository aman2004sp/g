@echo off
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install Python 3 and enable Add Python to PATH.
  pause
  exit /b 1
)
start "GATE PYQ Quiz" http://localhost:8000
python -m http.server 8000
pause
