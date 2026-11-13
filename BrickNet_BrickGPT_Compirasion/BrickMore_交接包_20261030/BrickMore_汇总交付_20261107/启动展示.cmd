@echo off
chcp 65001 >nul
cd /d "%~dp0"
python 展示\server.py 8140
pause
