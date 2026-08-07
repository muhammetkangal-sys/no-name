@echo off
chcp 65001 >nul

if not exist venv\Scripts\activate.bat (
    echo Sanal ortam bulunamadi. Once setup.bat calistirin.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
streamlit run app.py
