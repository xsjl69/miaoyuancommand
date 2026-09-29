@echo off
setlocal
set NSSM=C:\Users\admin\Downloads\nssm-2.24\nssm-2.24\win64\nssm.exe
set PY=C:\Users\admin\.workbuddy\binaries\python\envs\default\Scripts\python.exe
set DIR=D:\Code\miaoyuancommand\miaoyuancommand
set APP=%DIR%\app.py
set LOG=%DIR%\server.log
set LOGFILE=%DIR%\install.log

echo ===== miaoyuan service install ===== > "%LOGFILE%"

net session >nul 2>&1
if errorlevel 1 (echo [WARN] NOT admin >> "%LOGFILE%") else (echo [OK] admin >> "%LOGFILE%")

echo [*] nssm install miaoyuan >> "%LOGFILE%"
"%NSSM%" install miaoyuan "%PY%" >> "%LOGFILE%" 2>&1
echo [install exit=%ERRORLEVEL%] >> "%LOGFILE%"

"%NSSM%" set miaoyuan AppParameters "%APP%" >> "%LOGFILE%" 2>&1
"%NSSM%" set miaoyuan AppDirectory "%DIR%" >> "%LOGFILE%" 2>&1
"%NSSM%" set miaoyuan DisplayName "Miaoyuan Flask Server (13201)" >> "%LOGFILE%" 2>&1
"%NSSM%" set miaoyuan AppStdout "%LOG%" >> "%LOGFILE%" 2>&1
"%NSSM%" set miaoyuan AppStderr "%LOG%" >> "%LOGFILE%" 2>&1
"%NSSM%" set miaoyuan AppExit Default Restart >> "%LOGFILE%" 2>&1
"%NSSM%" set miaoyuan Start AUTO >> "%LOGFILE%" 2>&1

"%NSSM%" start miaoyuan >> "%LOGFILE%" 2>&1
echo [start exit=%ERRORLEVEL%] >> "%LOGFILE%"

echo [*] verify >> "%LOGFILE%"
"%NSSM%" get miaoyuan AppDirectory >> "%LOGFILE%" 2>&1

echo done. open install.log and send content back.
pause
