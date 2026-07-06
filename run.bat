@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found in %~dp0.venv
    echo Run this once first:
    echo   python -m venv .venv
    echo   .venv\Scripts\activate
    echo   pip install -r requirements.txt
    pause
    exit /b 1
)

if not exist ".env" (
    echo [ERROR] .env file not found.
    echo Copy .env.example to .env and fill in TG_API_ID / TG_API_HASH first.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
python -m tgparser.main search

echo.
echo Done. Press any key to close this window.
pause >nul
