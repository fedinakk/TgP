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

if not exist "queries.txt" (
    echo [ERROR] queries.txt not found.
    echo Copy queries.txt.example to queries.txt and add your post snippets first.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
python -m tgparser.main find-source

echo.
echo Done -- see out\lookup.md for results. Press any key to close this window.
pause >nul
