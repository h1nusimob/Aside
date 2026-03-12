@echo off
:: Detach python process from this cmd window entirely
where pythonw >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    start "" pythonw "%~dp0deskgoals.py"
) else (
    start "" python "%~dp0deskgoals.py"
)
