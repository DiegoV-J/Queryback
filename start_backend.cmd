@echo off
cd /d "%~dp0"
echo ========================================================
echo Iniciando Backend FastAPI en http://localhost:8000
echo Documentacion Swagger en http://localhost:8000/docs
echo ========================================================
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
pause
