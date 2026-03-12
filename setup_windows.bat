@echo off
setlocal
set STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set STARTMENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs
set VBS=%TEMP%\dg_setup.vbs

echo Creating shortcuts...

echo Set oWS = WScript.CreateObject("WScript.Shell") > "%VBS%"
echo Set oLink = oWS.CreateShortcut("%STARTUP%\DeskGoals.lnk") >> "%VBS%"
echo oLink.TargetPath = "%~dp0start.bat" >> "%VBS%"
echo oLink.WorkingDirectory = "%~dp0" >> "%VBS%"
echo oLink.WindowStyle = 7 >> "%VBS%"
echo oLink.Save >> "%VBS%"
cscript //nologo "%VBS%"

echo Set oWS = WScript.CreateObject("WScript.Shell") > "%VBS%"
echo Set oLink = oWS.CreateShortcut("%STARTMENU%\DeskGoals.lnk") >> "%VBS%"
echo oLink.TargetPath = "%~dp0start.bat" >> "%VBS%"
echo oLink.WorkingDirectory = "%~dp0" >> "%VBS%"
echo oLink.WindowStyle = 7 >> "%VBS%"
echo oLink.Save >> "%VBS%"
cscript //nologo "%VBS%"
del "%VBS%"

echo.
echo Launches on startup. Searchable in Start Menu.
echo Starting DeskGoals now...
start "" "%~dp0start.bat"
pause
