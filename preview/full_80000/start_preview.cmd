@echo off
cd /d "%~dp0"
where py >nul 2>&1
if errorlevel 1 goto usepython
py -3 launch_preview.py
goto finished
:usepython
python launch_preview.py
:finished
if errorlevel 1 pause
