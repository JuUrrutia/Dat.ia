@echo off
REM Script para compilar Datia a .exe en Windows

echo ============================================
echo    COMPILANDO DATIA A .EXE
echo ============================================
echo.

echo [1/4] Limpiando builds anteriores...
if exist dist (
    rmdir /s /q dist
    echo ✓ Carpeta dist eliminada
)
if exist dist-electron (
    rmdir /s /q dist-electron
    echo ✓ Carpeta dist-electron eliminada
)
echo.

echo [2/4] Compilando TypeScript...
call npx tsc
if %errorlevel% neq 0 (
    echo ✗ Error en compilación TypeScript
    exit /b 1
)
echo ✓ TypeScript compilado exitosamente
echo.

echo [3/4] Construyendo con Vite...
call npm run build:frontend 2>nul || call npx vite build
if %errorlevel% neq 0 (
    echo ✗ Error en build de Vite
    exit /b 1
)
echo ✓ Frontend compilado exitosamente
echo.

echo [4/4] Empaquetando con electron-builder...
call npx electron-builder
if %errorlevel% neq 0 (
    echo ✗ Error en electron-builder
    exit /b 1
)
echo ✓ Empaquetamiento completado
echo.

echo ============================================
echo    ✓ COMPILACION EXITOSA
echo ============================================
echo.
echo Los archivos .exe están en: dist/
echo.
echo Archivos generados:
echo   - Datia-X.X.X.exe (instalador NSIS)
echo   - Datia-X.X.X-portable.exe (ejecutable portátil)
echo.
pause
