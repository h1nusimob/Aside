@echo off
echo DeskGoals Debug Mode
echo Errors will appear here AND be saved to: %USERPROFILE%\deskgoals_error.log
echo.
python "%~dp0deskgoals.py"
echo.
echo ---- Exited. Check above for errors. ----
echo ---- Log file: %USERPROFILE%\deskgoals_error.log ----
pause
