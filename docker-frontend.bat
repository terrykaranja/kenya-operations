@echo off
REM Run commands in the frontend Docker container

if "%1"=="" (
    echo Usage: docker-frontend.bat [command]
    echo.
    echo Examples:
    echo   docker-frontend.bat npm install
    echo   docker-frontend.bat npm run build
    echo   docker-frontend.bat npm run lint
    echo   docker-frontend.bat sh
    exit /b 1
)

docker-compose exec frontend %*

if %ERRORLEVEL% NEQ 0 (
    echo Command failed with error code %ERRORLEVEL%
    exit /b %ERRORLEVEL%
)
