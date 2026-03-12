@echo off
echo Installing DeskGoals dependencies...
echo.
python -m pip install --upgrade pystray Pillow pywin32 psutil keyboard tkinterdnd2 pymupdf

echo.
echo Running pywin32 post-install...
python -c "import sys,os;s=os.path.join(sys.prefix,'Scripts','pywin32_postinstall.py');os.system('python \"'+s+'\" -install') if os.path.exists(s) else None" 2>nul

echo.
echo Adding Windows Firewall rules for file sharing...
netsh advfirewall firewall delete rule name="DeskGoals Share TCP" >nul 2>&1
netsh advfirewall firewall delete rule name="DeskGoals Discovery UDP" >nul 2>&1
netsh advfirewall firewall delete rule name="DeskGoals Sync TCP" >nul 2>&1
netsh advfirewall firewall add rule name="DeskGoals Share TCP"     dir=in action=allow protocol=TCP localport=7843
netsh advfirewall firewall add rule name="DeskGoals Discovery UDP" dir=in action=allow protocol=UDP localport=7844
netsh advfirewall firewall add rule name="DeskGoals Sync TCP"      dir=in action=allow protocol=TCP localport=7842
echo Firewall rules added.

echo.
echo Done. Run start.bat to launch.
echo Run debug.bat if it does not open.
echo.
echo NOTE: If devices still don't appear, re-run this file as Administrator
echo       (right-click install.bat -> Run as administrator)
pause
