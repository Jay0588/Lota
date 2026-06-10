@echo off
title JP.Trades - AI Trading Platform
cd /d "%~dp0"
echo.
echo  ========================================
echo   JP.Trades - Starting...
echo   Dashboard: http://127.0.0.1:5000
echo  ========================================
echo.
python app.py
pause
