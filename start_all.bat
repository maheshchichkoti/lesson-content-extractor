@echo off
REM Production startup script for Windows
echo ========================================
echo Starting Lesson Content Extractor
echo ========================================

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Start API server in background
echo Starting API server on port 8000...
start "API Server" cmd /k "python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload"

REM Wait 3 seconds for API to start
timeout /t 3 /nobreak

REM Start Zoom fetcher worker
echo Starting Zoom fetcher worker...
start "Zoom Fetcher" cmd /k "python fetcher.py"

REM Wait 2 seconds
timeout /t 2 /nobreak

REM Start Zoom processor worker
echo Starting Zoom processor worker...
start "Zoom Processor" cmd /k "python worker.py"

echo.
echo ========================================
echo All services started!
echo ========================================
echo API Server: http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo.
echo Press any key to stop all services...
pause
taskkill /FI "WindowTitle eq API Server*" /T /F
taskkill /FI "WindowTitle eq Zoom Fetcher*" /T /F
taskkill /FI "WindowTitle eq Zoom Processor*" /T /F
