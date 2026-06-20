@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
rem ============================================================
rem  Instala o handler do protocolo qgis:// (apenas usuario atual)
rem  Registra em HKCU\Software\Classes\qgis -> nao precisa de admin
rem ============================================================
set "HERE=%~dp0"

rem --- Localiza um interpretador pythonw (sem console) ---
set "PYW="
for %%P in (pythonw3.exe pythonw.exe) do (
  if not defined PYW for /f "delims=" %%i in ('where %%P 2^>nul') do (
    if not defined PYW set "PYW=%%i"
  )
)
if not defined PYW set "PYW=%LOCALAPPDATA%\Python\bin\pythonw3.exe"

if not exist "%PYW%" (
  echo [ERRO] Nao encontrei o pythonw. Edite este .bat e aponte a variavel PYW
  echo        para o seu pythonw.exe.
  pause
  exit /b 1
)

echo Usando interpretador: %PYW%
echo Pasta do handler:     %HERE%

reg add "HKCU\Software\Classes\qgis" /ve /t REG_SZ /d "URL:QGIS Protocol" /f >nul
reg add "HKCU\Software\Classes\qgis" /v "URL Protocol" /t REG_SZ /d "" /f >nul
reg add "HKCU\Software\Classes\qgis\shell\open\command" /ve /t REG_SZ /d "\"%PYW%\" \"%HERE%qgis_open.py\" \"%%1\"" /f >nul

if %errorlevel%==0 (
  echo.
  echo [OK] Handler qgis:// instalado com sucesso.
  echo      Teste:  start qgis://-24.281655,-49.695021
) else (
  echo [ERRO] Falha ao registrar o protocolo.
)
echo.
pause
