:: start.bat
@echo off
ECHO Starting PiSelfhosting Configurator...
ECHO This will open a new tab in your web browser.

:: Run the Flask application from the 'configurator_app' directory
python configurator_app/app.py

ECHO.
ECHO The server has been stopped. You can now close this window.
pause
