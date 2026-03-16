@echo off
echo Aside Debug Mode
echo Errors will appear here AND be saved to: %USERPROFILE%\aside_error.log
echo.
python "%~dp0aside.py"
echo.
echo ---- Exited. Check above for errors. ----
echo ---- Log file: %USERPROFILE%\aside_error.log ----
pause
