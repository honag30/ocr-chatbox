@echo off
title AI Document Chatbox System

echo   Starting AI Document Chatbox System (Clean Architecture)

start "AI Chatbox - Backend" cmd /k "cd /d "%~dp0backend" && python main.py"

timeout /t 2 /nobreak >nul

start "AI Chatbox - Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo Backend and Frontend started.
