@echo off
chcp 65001 > nul

echo.
echo  ========================================
echo   HR Excel Statistics Dashboard
echo  ========================================
echo.

REM Activate virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
    echo  [INFO] Activating virtual environment...
    call .venv\Scripts\activate.bat
)

REM Install dependencies
echo  [INFO] Installing packages...
pip install -r requirements.txt --quiet

echo.

REM Check if port 8501 is available, otherwise use 8502
set PORT=8501
netstat -ano | findstr ":8501 " | findstr "LISTENING" > nul
if %ERRORLEVEL% == 0 (
    echo  [WARN] Port 8501 is already in use. Using port 8502 instead.
    set PORT=8502
)

echo  [INFO] Starting app on port %PORT% ...
echo  [INFO] Open your browser at: http://localhost:%PORT%
echo.

python -m streamlit run app.py --server.port %PORT% --server.headless false

pause
