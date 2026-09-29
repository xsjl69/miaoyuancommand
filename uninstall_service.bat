@echo off
set NSSM=C:\Users\admin\Downloads\nssm-2.24\nssm-2.24\win64\nssm.exe
"%NSSM%" stop miaoyuan
"%NSSM%" remove miaoyuan confirm
echo Removed.
pause
