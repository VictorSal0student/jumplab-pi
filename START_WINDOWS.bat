@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel% equ 0 (
    py -3 start_pc.py
) else (
    python start_pc.py
)
echo.
pause
