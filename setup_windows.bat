@echo off
setlocal
cd /d "%~dp0"
py -m venv .venv
call .venv\Scripts\activate
pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File setup_official_assets.ps1
echo.
echo Set your key with:
echo   set SPOONACULAR_API_KEY=YOUR_KEY
echo Then run:
echo   python app.py
pause
