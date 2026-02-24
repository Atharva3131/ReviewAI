@echo off
echo ========================================
echo Starting ReviewAI Development Environment
echo ========================================
echo.

REM Kill any existing processes first
echo Stopping any existing processes...
taskkill /F /IM python.exe /T 2>nul
taskkill /F /IM node.exe /T 2>nul
timeout /t 2 /nobreak > nul

REM Start Backend
echo [1/2] Starting Backend Server...
start "ReviewAI Backend" cmd /k "cd backend && venv\Scripts\activate && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

REM Wait a bit for backend to start
timeout /t 5 /nobreak > nul

REM Start Frontend
echo [2/2] Starting Frontend Server...
start "ReviewAI Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ========================================
echo ReviewAI is starting up!
echo ========================================
echo.
echo Backend:  http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo Frontend: http://localhost:3000
echo.
echo Press any key to open the application in your browser...
pause > nul

REM Open browser
start http://localhost:3000

echo.
echo Both servers are running in separate windows.
echo Close those windows to stop the servers.
echo.
pause
