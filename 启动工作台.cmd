@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
if not defined TRAVEL_PORT set TRAVEL_PORT=8790
if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
  if errorlevel 1 goto fail
)
".venv\Scripts\python.exe" -c "import fastapi,uvicorn,httpx,dotenv,pytest" >nul 2>&1
if errorlevel 1 (
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 goto fail
)
if not exist .env copy /y .env.example .env >nul
echo Open http://127.0.0.1:%TRAVEL_PORT% - press Ctrl+C to stop.
".venv\Scripts\python.exe" -m uvicorn api.main:app --host 127.0.0.1 --port %TRAVEL_PORT%
if errorlevel 1 goto fail
exit /b 0
:fail
echo Startup failed. Python 3.9+ is required. Check the error above.
pause
exit /b 1
