@echo off
REM Build Docker containers for SEZ Ledger development

echo Building Docker containers...
docker-compose build

if %ERRORLEVEL% EQU 0 (
    echo Build completed successfully!
) else (
    echo Build failed with error code %ERRORLEVEL%
    exit /b %ERRORLEVEL%
)
