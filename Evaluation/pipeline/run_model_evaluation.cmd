@echo off
set "EVAL_ROOT=D:\PythonEnvs\brickmore-eval"
set "TEMP=%EVAL_ROOT%\cache\temp"
set "TMP=%TEMP%"
set "TMPDIR=%TEMP%"
set "HF_HOME=%EVAL_ROOT%\cache\huggingface"
set "PIP_CACHE_DIR=%EVAL_ROOT%\cache\pip"
set "TOKENIZERS_PARALLELISM=false"
set "PYEXE=%EVAL_ROOT%\Scripts\python.exe"
if not exist "%PYEXE%" goto failed
pushd "%~dp0..\.."
set "OUT=Results\model_eval_20261021"
if not exist "%OUT%\manifest.jsonl" "%PYEXE%" Evaluation\pipeline\evaluate_models.py manifest --out "%OUT%"
if errorlevel 1 goto failed
"%PYEXE%" -u Evaluation\pipeline\download_models.py --output "%HF_HOME%\models"
if errorlevel 1 goto failed
"%PYEXE%" -u Evaluation\pipeline\evaluate_models.py render --out "%OUT%"
if errorlevel 1 goto failed
"%PYEXE%" -u Evaluation\pipeline\evaluate_models.py score --metric siglip2 --out "%OUT%"
if errorlevel 1 goto failed
"%PYEXE%" -u Evaluation\pipeline\evaluate_models.py score --metric pe --out "%OUT%"
if errorlevel 1 goto failed
"%PYEXE%" -u Evaluation\pipeline\evaluate_models.py summarize --out "%OUT%"
if errorlevel 1 goto failed
"%PYEXE%" -u Evaluation\pipeline\make_report.py --out "%OUT%"
if errorlevel 1 goto failed
echo Evaluation completed. Results: %CD%\%OUT%
popd
pause
exit /b 0

:failed
echo Evaluation did not finish. Inspect the error above; completed records can be resumed.
pause
exit /b 1
