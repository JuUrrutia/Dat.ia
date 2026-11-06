const { spawnSync } = require('child_process');
const path = require('path');
const findPython = require('./find-python');

const rootDir = path.join(__dirname, '..');
const backendDir = path.join(rootDir, 'backend');
const scriptPath = path.join(backendDir, 'scripts', 'setup_postgres_full.py');
const pythonCmd = findPython(backendDir);

if (!pythonCmd) {
  console.error('[PYTHON] No se encontró un intérprete con FastAPI, SQLAlchemy y Uvicorn instalados.');
  console.error('[PYTHON] Repara backend\\venv o instala backend\\requirements.txt en un Python disponible.');
  process.exit(1);
}

console.log(`\n[DB-BOOTSTRAP] Ejecutando inicialización y verificación de PostgreSQL con: ${pythonCmd}...`);

const env = findPython.pythonEnv({
  PYTHONPATH: backendDir,
  PYTHONUNBUFFERED: '1',
});

const result = spawnSync(pythonCmd, [scriptPath], {
  cwd: rootDir,
  env,
  stdio: 'inherit',
});

if (result.error) {
  console.error(`[DB-BOOTSTRAP] No se pudo ejecutar el script: ${result.error.message}`);
  process.exit(1);
}

// Propagate the script's exit code. Exit 0 unconditionally reported a
// successful bootstrap even when setup_postgres_full.py failed, so a Docker
// build went green with the metadata schema never created.
if (result.status !== 0) {
  console.error(`[DB-BOOTSTRAP] setup_postgres_full.py falló con código ${result.status}.`);
  process.exit(result.status || 1);
}

console.log('[DB-BOOTSTRAP] PostgreSQL inicializado y verificado.');
