@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv (
  echo Dang chuan bi lan dau, vui long cho vai phut...
  python -m venv .venv
)
.venv\Scripts\python -m pip install -q -r requirements.txt
echo Phan mem dang chay. Dung dong cua so nay khi dang dung.
start "" cmd /c "timeout /t 5 >nul & start http://localhost:8501"
.venv\Scripts\python -m streamlit run app.py
pause
