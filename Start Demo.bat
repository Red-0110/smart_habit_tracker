@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  py -3 demo.py setup
  if errorlevel 1 exit /b 1
)
py -3 demo.py run --open
pause
