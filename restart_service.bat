@echo off
setlocal
rem miaoyuan service: ensure running (install if missing, else restart)
set NSSM=C:\Users\admin\Downloads\nssm-2.24\nssm-2.24\win64\nssm.exe
set PY=C:\Users\admin\.workbuddy\binaries\python\envs\default\Scripts\python.exe
set DIR=D:\Code\miaoyuancommand\miaoyuancommand
set APP=%DIR%\app.py
set LOG=%DIR%\server.log
set LOGFILE=%DIR%\restart.log

echo ===== miaoyuan service ensure-running ===== > "%LOGFILE%"

net session >nul 2>&1
if errorlevel 1 (echo [WARN] NOT admin >> "%LOGFILE%") else (echo [OK] admin >> "%LOGFILE%")

rem --- does the service exist? ---
sc query miaoyuan >nul 2>&1
if errorlevel 1 goto INSTALL

echo [*] service exists -> stop >> "%LOGFILE%"
"%NSSM%" stop miaoyuan >> "%LOGFILE%" 2>&1
goto AFTERSTOP

:INSTALL
echo [*] service NOT found -> install >> "%LOGFILE%"
"%NSSM%" install miaoyuan "%PY%" >> "%LOGFILE%" 2>&1
"%NSSM%" set miaoyuan AppParameters "%APP%" >> "%LOGFILE%" 2>&1
"%NSSM%" set miaoyuan AppDirectory "%DIR%" >> "%LOGFILE%" 2>&1
"%NSSM%" set miaoyuan DisplayName "Miaoyuan Flask Server (13201)" >> "%LOGFILE%" 2>&1
"%NSSM%" set miaoyuan AppStdout "%LOG%" >> "%LOGFILE%" 2>&1
"%NSSM%" set miaoyuan AppStderr "%LOG%" >> "%LOGFILE%" 2>&1
"%NSSM%" set miaoyuan AppExit Default Restart >> "%LOGFILE%" 2>&1
"%NSSM%" set miaoyuan Start AUTO >> "%LOGFILE%" 2>&1

:AFTERSTOP
echo [*] kill stale process holding 13201 >> "%LOGFILE%"
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":13201" ^| findstr "LISTENING"') do (
  echo   killing PID %%p >> "%LOGFILE%"
  taskkill /F /PID %%p >> "%LOGFILE%" 2>&1
)

echo [*] start service >> "%LOGFILE%"
"%NSSM%" start miaoyuan >> "%LOGFILE%" 2>&1

timeout /t 3 /nobreak >nul

echo [*] listeners on 13201 >> "%LOGFILE%"
netstat -ano | findstr ":13201" >> "%LOGFILE%" 2>&1

echo [*] server.log tail >> "%LOGFILE%"
if exist "%DIR%\server.log" type "%DIR%\server.log" >> "%LOGFILE%" 2>&1

echo done. see restart.log
pause
