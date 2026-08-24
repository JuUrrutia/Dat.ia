const { spawnSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const rootDir = path.join(__dirname, '..');
const backendDir = path.join(rootDir, 'backend');
const scriptPath = path.join(backendDir, 'scripts', 'bootstrap_postgres.py');

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
  console.warn(`[DB-BOOTSTRAP] Nota: No se pudo ejecutar el script de verificación (${result.error.message}).`);
}

process.exit(0);
