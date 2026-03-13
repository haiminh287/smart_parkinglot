@echo off
REM ============================================================
REM  AI Service — Local Development Startup Script
REM  Run from: backend-microservices\ai-service-fastapi\
REM ============================================================

echo ============================================================
echo  ParkSmart AI Service - Local Development
echo ============================================================
echo.

REM -- Store the script directory as AI_DIR --
set "AI_DIR=%~dp0"
REM Remove trailing backslash
if "%AI_DIR:~-1%"=="\" set "AI_DIR=%AI_DIR:~0,-1%"

REM -- Database (MySQL on localhost:3307) --
set DB_HOST=localhost
set DB_PORT=3307
set DB_NAME=parksmartdb
set DB_USER=root
set DB_PASSWORD=parksmartpass

REM -- Debug --
set DEBUG=True

REM -- Gateway Secret --
set GATEWAY_SECRET=gateway-internal-secret-key

REM -- Media / ML paths --
set MEDIA_ROOT=%AI_DIR%\media
set ML_MODELS_DIR=%AI_DIR%\ml\models
set PLATE_MODEL_PATH=%AI_DIR%\app\models\license-plate-finetune-v1m.pt

REM -- Sibling service URLs (local ports) --
set PARKING_SERVICE_URL=http://localhost:8003
set BOOKING_SERVICE_URL=http://localhost:8002
set REALTIME_SERVICE_URL=http://localhost:8006

REM -- Create media directory if it doesn't exist --
if not exist "%MEDIA_ROOT%" (
    mkdir "%MEDIA_ROOT%"
    echo Created media directory: %MEDIA_ROOT%
)

REM -- Pre-flight checks --
echo [CHECK] Verifying virtual environment...
if not exist "%AI_DIR%\venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found at %AI_DIR%\venv\
    echo         Create it with: python -m venv venv
    pause
    exit /b 1
)

echo [CHECK] Verifying plate model file...
if not exist "%PLATE_MODEL_PATH%" (
    echo [WARN]  Plate model not found: %PLATE_MODEL_PATH%
    echo         License plate detection will NOT work until model is placed there.
) else (
    echo [OK]    Plate model found.
)

echo.
echo -- Environment Variables --
echo   DB_HOST=%DB_HOST%
echo   DB_PORT=%DB_PORT%
echo   DB_NAME=%DB_NAME%
echo   MEDIA_ROOT=%MEDIA_ROOT%
echo   PLATE_MODEL_PATH=%PLATE_MODEL_PATH%
echo   PARKING_SERVICE_URL=%PARKING_SERVICE_URL%
echo   BOOKING_SERVICE_URL=%BOOKING_SERVICE_URL%
echo   REALTIME_SERVICE_URL=%REALTIME_SERVICE_URL%
echo.

REM -- Activate venv and run --
echo [START] Activating venv and starting uvicorn on port 8009...
echo ============================================================
call "%AI_DIR%\venv\Scripts\activate.bat"

cd /d "%AI_DIR%"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8009 --reload

REM -- If uvicorn exits --
echo.
echo [STOP] AI Service stopped.
pause
