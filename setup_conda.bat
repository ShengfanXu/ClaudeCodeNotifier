@echo off
cd /d "%~dp0"
echo Creating conda environment 'claude-notifier' with Python 3.12...

call conda create -n claude-notifier python=3.12 -y
echo.

echo Installing pip dependencies...

call conda run -n claude-notifier pip install -r requirements.txt
echo.

echo Setup complete. Use run.bat to start the app.
pause