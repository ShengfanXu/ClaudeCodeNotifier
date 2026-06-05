@echo off
cd /d "%~dp0"

call conda activate claude-notifier
python -m src.main

echo 程序退出码：%errorlevel%
pause