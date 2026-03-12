@echo off
echo Uninstalling DeskGoals Python dependencies...
python -m pip uninstall pystray Pillow pywin32 psutil keyboard tkinterdnd2 -y

echo.
echo Removing Windows Firewall rules...
netsh advfirewall firewall delete rule name="DeskGoals Share TCP" >nul 2>&1
netsh advfirewall firewall delete rule name="DeskGoals Discovery UDP" >nul 2>&1
netsh advfirewall firewall delete rule name="DeskGoals Sync TCP" >nul 2>&1
echo Firewall rules removed.

echo.
echo Cleanup complete!
pause