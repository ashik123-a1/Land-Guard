@echo off
title LandGuard AI - Land Record Verification Platform
color 0B

echo ===============================================================================
echo            LANDGUARD AI - FRAUD ^& DOUBLE-SELLING VERIFICATION PLATFORM
echo                           LandTech 2026 Production Release
echo ===============================================================================
echo.

:: Change to script directory
cd /d "%~dp0"

:: Check if Python is available
where python >nul 2>nul
if %errorlevel% neq 0 (
    if exist "C:\Users\ASHIK_CSE\AppData\Local\Programs\Python\Python311\python.exe" (
        set "PYTHON_CMD=C:\Users\ASHIK_CSE\AppData\Local\Programs\Python\Python311\python.exe"
    ) else (
        echo [ERROR] Python was not found in your PATH or standard install directory.
        echo Please ensure Python 3.11+ is installed and added to PATH.
        pause
        exit /b 1
    )
) else (
    set "PYTHON_CMD=python"
)

echo [OK] Using Python: %PYTHON_CMD%
echo.
echo -------------------------------------------------------------------------------
echo Application Access URLs:
echo   - Home / Landing Page:       http://127.0.0.1:8000
echo   - Citizen Dashboard:         http://127.0.0.1:8000/user/dashboard
echo   - Voice Assistant (Bangla):  http://127.0.0.1:8000/user/voice
echo   - Admin Command Center:      http://127.0.0.1:8000/admin/dashboard
echo.
echo Demo Accounts:
echo   - Citizen:      citizen@landguard.gov.bd      / Citizen@123
echo   - Investigator: investigator@landguard.gov.bd / Investigator@123
echo   - Admin:        admin@landguard.gov.bd        / Admin@123
echo -------------------------------------------------------------------------------
echo.
echo Starting LandGuard Uvicorn Server on http://127.0.0.1:8000 ...
echo Opening your web browser automatically in 3 seconds...
echo.

:: Launch browser in background after 3 seconds
start /b cmd /c "timeout /t 3 /nobreak >nul & start http://127.0.0.1:8000"

:: Start Uvicorn Server
%PYTHON_CMD% -m uvicorn src.landguard_web.app:app --host 127.0.0.1 --port 8000 --reload

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] The LandGuard server stopped unexpectedly with error code %errorlevel%.
    pause
)
