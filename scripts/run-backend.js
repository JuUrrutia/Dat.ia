const { spawnSync, spawn } = require('child_process');
const path = require('path');
const findPython = require('./find-python');

const backendDir = path.join(__dirname, '..', 'backend');
const pythonCmd = findPython(backendDir);

if (!pythonCmd) {
  console.error('[PYTHON] No se encontró un intérprete con FastAPI, SQLAlchemy y Uvicorn instalados.');
  console.error('[PYTHON] Repara backend\\venv o instala backend\\requirements.txt en un Python disponible.');
  process.exit(1);
}

// 3. PostgreSQL Service & Auto-Provisioning Check
if (process.platform === 'win32') {
  try {
    const svcCheck = spawnSync('powershell', ['-NoProfile', '-Command', '(Get-Service *postgres* -ErrorAction SilentlyContinue).Status'], { encoding: 'utf-8' });
    if (svcCheck.stdout && svcCheck.stdout.trim().toLowerCase().includes('stopped')) {
      console.log('[DB-SERVICE] Servicio PostgreSQL detenido. Intentando iniciar servicio...');
      spawnSync('powershell', ['-NoProfile', '-Command', 'Start-Service *postgres* -ErrorAction SilentlyContinue']);
    }
  } catch (_) {}
}

console.log(`\n[BACKEND-RUNNER] Ejecutando backend FastAPI con: ${pythonCmd}`);

const child = spawn(pythonCmd, ['main.py'], {
  cwd: backendDir,
  stdio: 'inherit',
  env: findPython.pythonEnv(),
});

child.on('exit', (code) => {
  process.exit(code || 0);
});
