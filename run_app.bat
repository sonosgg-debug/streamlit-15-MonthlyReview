@echo off
cd /d "%~dp0"
title Economic Indicators Review ^& Preview

echo ========================================================
echo   Economic Indicators Review ^& Preview Dashboard
echo   Starting Streamlit Application...
echo   Local URL: http://localhost:8501
echo ========================================================
echo.

python -m streamlit run app.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo [Error] Failed to run the application. (Error code: %ERRORLEVEL%)
    echo.
)

pause
