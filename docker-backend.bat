@echo off
REM Run commands in the backend Docker container

if "%1"=="" (
    echo Usage: docker-backend.bat [command]
    echo.
    echo Examples:
    echo   docker-backend.bat python -m app.cli.create_user admin password123 --admin
    echo   docker-backend.bat python -m app.import_legacy resources/Seza_Stock_Ledger_Hackathon.xlsx
    echo   docker-backend.bat pytest
    echo   docker-backend.bat alembic upgrade head
    echo   docker-backend.bat bash
    exit /b 1
)

docker-compose exec backend %*

if %ERRORLEVEL% NEQ 0 (
    echo Command failed with error code %ERRORLEVEL%
    exit /b %ERRORLEVEL%
)
