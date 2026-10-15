@echo off
cd /d "%~dp0backend"
if not exist ".venv\Scripts\python.exe" (
  py -3.12 -m venv .venv
)
call .venv\Scripts\activate
if not exist ".env" copy .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8111 --reload
