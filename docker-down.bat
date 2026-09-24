@echo off
REM Stop Docker containers for SEZ Ledger development

echo Stopping Docker containers...
docker-compose down

if %ERRORLEVEL% EQU 0 (
    echo Containers stopped successfully!
) else (
    echo Failed to stop containers with error code %ERRORLEVEL%
    exit /b %ERRORLEVEL%
)
