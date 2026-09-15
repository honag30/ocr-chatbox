@echo off
title AI Document Chatbox System

echo   Starting AI Document Chatbox System (Clean Architecture)

start "AI Chatbox - Backend" cmd /k "cd /d "%~dp0backend" && set "PYTHONPATH=%~dp0;%~dp0backend" && python main.py"

%SystemRoot%\System32\timeout.exe /t 2 /nobreak >nul 2>&1 || ping 127.0.0.1 -n 3 >nul

start "AI Chatbox - Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo Backend and Frontend started.
echo Backend: http://127.0.0.1:8000
echo Frontend: http://localhost:5173

