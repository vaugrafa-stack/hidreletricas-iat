@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
rem ============================================================
rem  Instala o handler do protocolo gearth:// (Google Earth Pro)
rem  Registra em HKCU\Software\Classes\gearth -> nao precisa admin
rem ============================================================
set "HERE=%~dp0"

set "PYW="
for %%P in (pythonw3.exe pythonw.exe) do (
  if not defined PYW for /f "delims=" %%i in ('where %%P 2^>nul') do (
    if not defined PYW set "PYW=%%i"
  )
)
if not defined PYW set "PYW=%LOCALAPPDATA%\Python\bin\pythonw3.exe"

if not exist "%PYW%" (
  echo [ERRO] Nao encontrei o pythonw. Edite este .bat e aponte PYW para o seu pythonw.exe.
  pause
  exit /b 1
)

echo Usando interpretador: %PYW%
echo Pasta do handler:     %HERE%

reg add "HKCU\Software\Classes\gearth" /ve /t REG_SZ /d "URL:Google Earth Protocol" /f >nul
reg add "HKCU\Software\Classes\gearth" /v "URL Protocol" /t REG_SZ /d "" /f >nul
reg add "HKCU\Software\Classes\gearth\shell\open\command" /ve /t REG_SZ /d "\"%PYW%\" \"%HERE%gearth_open.py\" \"%%1\"" /f >nul

if %errorlevel%==0 (
  echo.
  echo [OK] Handler gearth:// instalado com sucesso.
  echo      Teste:  start gearth://-24.281655,-49.695021
) else (
  echo [ERRO] Falha ao registrar o protocolo.
)
echo.
pause
