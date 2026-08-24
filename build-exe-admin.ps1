# Script para generar .EXE con permisos de administrador
# Pide permisos elevados si no los tiene

# Verificar si está ejecutando como administrador
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "⚠️  Se requieren permisos de administrador para generar el .EXE" -ForegroundColor Yellow
    Write-Host "Pidiendo permisos elevados..." -ForegroundColor Cyan
    
    # Re-ejecutar script como administrador
    Start-Process PowerShell -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

Write-Host "✓ Ejecutando como administrador" -ForegroundColor Green
Write-Host ""

# Cambiar a directorio del proyecto
$projectPath = "d:\Duoc\8vo Semestre 2025\Capston\Datia"
cd $projectPath

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "    GENERANDO DATIA .EXE" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Paso 1: Limpiar caché
Write-Host "[1/4] Limpiando caché de electron-builder..." -ForegroundColor Yellow
Remove-Item -Recurse -Force "$env:APPDATA\electron-builder" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "dist" -ErrorAction SilentlyContinue
Write-Host "✓ Caché limpiado" -ForegroundColor Green
Write-Host ""

# Paso 2: Compilar TypeScript
Write-Host "[2/4] Compilando TypeScript..." -ForegroundColor Yellow
npx tsc
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Error en TypeScript" -ForegroundColor Red
    exit 1
}
Write-Host "✓ TypeScript compilado" -ForegroundColor Green
Write-Host ""

# Paso 3: Construir frontend
Write-Host "[3/4] Construyendo frontend con Vite..." -ForegroundColor Yellow
npm run build:frontend
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Error en Vite build" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Frontend compilado" -ForegroundColor Green
Write-Host ""

# Paso 4: Empaquetar con electron-builder
Write-Host "[4/4] Empaquetando con electron-builder..." -ForegroundColor Yellow
npx electron-builder
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Error en electron-builder" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Empaquetamiento completado" -ForegroundColor Green
Write-Host ""

Write-Host "============================================" -ForegroundColor Green
Write-Host "    ✓ COMPILACION EXITOSA" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "El archivo .EXE está en: dist/" -ForegroundColor Cyan
Write-Host ""

# Listar archivos generados
Get-ChildItem "dist" -Filter "*.exe" | ForEach-Object {
    Write-Host "  ✓ $_" -ForegroundColor Green
}

Write-Host ""
Write-Host "Presiona ENTER para cerrar..." -ForegroundColor Gray
Read-Host
