@echo off
cd /d D:\Code\miaoyuancommand\miaoyuancommand
:loop
echo [%date% %time%] starting flask >> server.log
"C:\Users\admin\.workbuddy\binaries\python\envs\default\Scripts\python.exe" app.py >> server.log 2>&1
echo [%date% %time%] flask exited, restart in 3s >> server.log
timeout /t 3 /nobreak >nul
goto loop
