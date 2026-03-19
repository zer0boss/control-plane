@echo off
echo Starting OpenClaw Control Plane Backend...
cd /d "%~dp0"
python -m uvicorn app.main:socket_app --host 0.0.0.0 --port 8001 --reload
pause