@echo off
title AI Document Chatbox System

echo ======================================================
echo   Starting AI Document Chatbox (Frontend + Backend)
echo   Backend:  http://127.0.0.1:8000
echo   Frontend: http://localhost:5173
echo ======================================================

set "PYTHONPATH=%~dp0;%~dp0backend"
npx --yes concurrently --kill-others -n "BACKEND,FRONTEND" -c "blue.bold,green.bold" "cd backend && python main.py" "cd frontend && npm run dev"
