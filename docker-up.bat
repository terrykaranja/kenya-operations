@echo off
REM Start Docker containers for SEZ Ledger development

echo Starting Docker containers...
docker-compose up -d

if %ERRORLEVEL% EQU 0 (
    echo Containers started successfully!
    echo.
    echo Backend API: http://localhost:8000
    echo API Docs: http://localhost:8000/docs
    echo Frontend: http://localhost:5173
    echo.
    echo To view logs, run: docker-compose logs -f
    echo To stop containers, run: docker-down.bat
) else (
    echo Failed to start containers with error code %ERRORLEVEL%
    exit /b %ERRORLEVEL%
)
