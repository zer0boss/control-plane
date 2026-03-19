@echo off
echo Starting OpenClaw Control Plane...
echo.
echo Starting Backend on port 8001...
start "Control Plane Backend" cmd /k "cd /d %~dp0backend && start.bat"
timeout /t 2 /nobreak >nul
echo Starting Frontend...
start "Control Plane Frontend" cmd /k "cd /d %~dp0frontend && start.bat"
echo.
echo Backend: http://localhost:8001
echo Frontend: http://localhost:3000
echo API Docs: http://localhost:8001/docs
echo.
pause