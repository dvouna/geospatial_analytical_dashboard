@echo off
REM Streamlit App Startup Script for Windows

echo.
echo ============================================================
echo  STREAMLIT DATA VISUALIZATION & AI QUERY APP
echo ============================================================
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Check if dependencies are installed
python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo.
    echo Installing dependencies...
    echo This may take a few minutes...
    echo.
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
)

REM Run verification
echo.
echo Verifying setup...
python verify_syntax.py
if errorlevel 1 (
    echo.
    echo ERROR: Verification failed
    pause
    exit /b 1
)

REM Start Streamlit app
echo.
echo ============================================================
echo  Starting Streamlit App
echo ============================================================
echo.
echo The app will open at: http://localhost:8501
echo Press Ctrl+C to stop the server
echo.

streamlit run app.py

pause
