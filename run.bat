@echo off
cd /d "%~dp0"

if not exist ".env" (
    echo Creating .env file...
    echo # Kapil Spread Algo - environment variables > .env
    echo .env created.
) else (
    echo .env already exists.
)

echo Installing dependencies from requirements.txt...
pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install requirements.
    pause
    exit /b 1
)

echo Starting app and opening browser in 4 seconds...
start cmd /c "timeout /t 4 /nobreak > nul && start http://127.0.0.1:5000"

python main.py
pause
