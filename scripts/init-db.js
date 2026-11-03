const { spawnSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const rootDir = path.join(__dirname, '..');
const backendDir = path.join(rootDir, 'backend');
const scriptPath = path.join(backendDir, 'scripts', 'setup_postgres_full.py');

// 1. Check local virtual environment paths
const candidates = [
  path.join(backendDir, 'venv', 'Scripts', 'python.exe'),
  path.join(backendDir, '.venv', 'Scripts', 'python.exe'),
  path.join(backendDir, 'venv', 'bin', 'python'),
  path.join(backendDir, '.venv', 'bin', 'python'),
];

let pythonCmd = null;

for (const cand of candidates) {
  if (fs.existsSync(cand)) {
    pythonCmd = cand;
    break;
  }
}

// 2. If no virtualenv found, probe system Python commands
if (!pythonCmd) {
  const probeCommands = process.platform === 'win32'
    ? ['py', 'python', 'python3']
    : ['python3', 'python'];

  for (const cmd of probeCommands) {
    try {
      const res = spawnSync(cmd, ['--version'], { encoding: 'utf-8' });
      if (res.status === 0 && ((res.stdout && res.stdout.toLowerCase().includes('python')) || (res.stderr && res.stderr.toLowerCase().includes('python')))) {
        pythonCmd = cmd;
        break;
      }
    } catch (_) {
      // try next
    }
  }
}

if (!pythonCmd) {
  pythonCmd = process.platform === 'win32' ? 'py' : 'python3';
}

console.log(`\n[DB-BOOTSTRAP] Ejecutando inicialización y verificación de PostgreSQL con: ${pythonCmd}...`);

const env = {
  ...process.env,
  PYTHONPATH: backendDir,
  PYTHONUNBUFFERED: '1',
};

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
