@echo off
cd /d "%~dp0"
conda run -n claude-notifier python -m src.main
pause
