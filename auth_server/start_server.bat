@echo off
title Avanture Central Auth Server & Web Dashboard
echo ============================================================
echo   Starting Avanture Central Auth Server
echo   Web Dashboard: http://localhost:8000/dashboard
echo ============================================================
echo.
python -m uvicorn server:app --app-dir "%~dp0" --host 0.0.0.0 --port 8000 --reload
pause

