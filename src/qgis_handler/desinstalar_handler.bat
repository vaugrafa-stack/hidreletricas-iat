@echo off
chcp 65001 >nul
rem Remove o handler do protocolo qgis:// do usuario atual.
reg delete "HKCU\Software\Classes\qgis" /f >nul 2>&1
if %errorlevel%==0 (
  echo [OK] Handler qgis:// removido.
) else (
  echo [INFO] Nada para remover (handler nao estava instalado).
)
echo.
pause
