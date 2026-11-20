@echo off
cd /d "%~dp0"
echo ========================================================
echo Iniciando Dashboard Vite/React en http://localhost:5173
echo ========================================================
.\.hackathon\.tools\node\npm.cmd --prefix dashboard run dev
pause
