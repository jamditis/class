@echo off
echo ====================================
echo Fathom Webhook Server for STCM140
echo ====================================
echo.
echo Starting server on http://localhost:5050
echo.
echo To expose publicly, run in another terminal:
echo   ngrok http 5050
echo.
echo Then add the ngrok URL to Fathom webhook settings.
echo ====================================
echo.
python fathom_webhook_server.py
pause
