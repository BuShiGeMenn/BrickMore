@echo off
setlocal
set "PYTHONUTF8=1"
set "PAPER_ENV=D:\PythonEnvs\brickmore-paper"
set "TEMP=%PAPER_ENV%\cache\temp"
set "TMP=%TEMP%"
set "TMPDIR=%TEMP%"
set "HF_HOME=%PAPER_ENV%\cache\huggingface"
set "PIP_CACHE_DIR=%PAPER_ENV%\cache\pip"
set "BRICKNET_DATA=%PAPER_ENV%\cache\bricknet-v010"
set "TOKENIZERS_PARALLELISM=false"
set "PYEXE=%PAPER_ENV%\Scripts\python.exe"
if not exist "%PYEXE%" (
  echo Run setup_paper_environment.cmd cpu or cuda first.
  exit /b 1
)
if not exist "%TEMP%" mkdir "%TEMP%"
if /i "%~1"=="audit" (
  "%PYEXE%" "%~dp0audit_paper_eval.py"
  exit /b
)
if /i "%~1"=="structure" (
  if "%~3"=="" goto usage
  "%PYEXE%" "%~dp0evaluate_structure.py" --input "%~2" --out "%~3" --data-dir "%BRICKNET_DATA%"
  exit /b
)
if /i "%~1"=="images" (
  if "%~5"=="" goto usage
  "%PYEXE%" "%~dp0evaluate_paper_images.py" --metric "%~2" --preset "%~3" --renders "%~4" --out "%~5"
  exit /b
)
:usage
echo Usage:
echo   run_paper_evaluation.cmd audit
echo   run_paper_evaluation.cmd structure generated.jsonl structure.jsonl
echo   run_paper_evaluation.cmd images vqa local renders.jsonl vqa.jsonl
echo Image scoring needs setup_paper_environment.cmd cuda. Full paper models need sufficient hardware.
exit /b 2
