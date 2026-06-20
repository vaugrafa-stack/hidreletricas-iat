@echo off
chcp 65001 >nul
rem Remove o handler do protocolo gearth:// do usuario atual.
reg delete "HKCU\Software\Classes\gearth" /f >nul 2>&1
if %errorlevel%==0 (
  echo [OK] Handler gearth:// removido.
) else (
  echo [INFO] Nada para remover.
)
echo.
pause
