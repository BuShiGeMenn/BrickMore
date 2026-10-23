@echo off
setlocal
set "PYTHONUTF8=1"
set "PAPER_ENV=D:\PythonEnvs\brickmore-paper"
set "BASE_PY=C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe"
set "TEMP=%PAPER_ENV%\cache\temp"
set "TMP=%TEMP%"
set "TMPDIR=%TEMP%"
set "PIP_CACHE_DIR=%PAPER_ENV%\cache\pip"
set "HF_HOME=%PAPER_ENV%\cache\huggingface"
set "BRICKNET_DATA=%PAPER_ENV%\cache\bricknet-v010"
set "TOKENIZERS_PARALLELISM=false"
set "MODE=%~1"
if "%MODE%"=="" set "MODE=cpu"
if /i not "%MODE%"=="cpu" if /i not "%MODE%"=="cuda" goto usage
if not exist "%TEMP%" mkdir "%TEMP%"
if not exist "%PAPER_ENV%\Scripts\python.exe" (
  "%BASE_PY%" -m venv "%PAPER_ENV%"
  if errorlevel 1 exit /b 1
)
set "PYEXE=%PAPER_ENV%\Scripts\python.exe"
if /i "%MODE%"=="cuda" (
  "%PYEXE%" -m pip install torch==2.8.0 torchvision==0.23.0 --index-url https://download.pytorch.org/whl/cu128
  if errorlevel 1 exit /b 1
  "%PYEXE%" -m pip install -r "%~dp0requirements-paper-gpu.txt"
) else (
  "%PYEXE%" -m pip install -r "%~dp0requirements-paper-core.txt"
)
if errorlevel 1 exit /b 1
"%PYEXE%" -m pip check
if errorlevel 1 exit /b 1
"%PYEXE%" -m pip freeze > "%PAPER_ENV%\requirements-lock.txt"
echo Environment ready: %PAPER_ENV%
echo To download original collision meshes, set BRICKNET_DATA=%BRICKNET_DATA%
echo and run "%PYEXE%" -m bricknet fetch-meshes
exit /b 0
:usage
echo Usage: setup_paper_environment.cmd cpu ^| cuda
exit /b 2
