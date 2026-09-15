const { spawnSync, spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const backendDir = path.join(__dirname, '..', 'backend');

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
  // Fallback to py on Windows or python3 on Unix
  pythonCmd = process.platform === 'win32' ? 'py' : 'python3';
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

console.log(`[DB-BOOTSTRAP] Verificando bases de datos PostgreSQL y datos base...`);
const setupScript = path.join(backendDir, 'scripts', 'setup_postgres_full.py');
try {
  spawnSync(pythonCmd, [setupScript], {
    cwd: path.join(__dirname, '..'),
    stdio: 'inherit',
    env: {
      ...process.env,
      PYTHONPATH: backendDir,
      PYTHONUNBUFFERED: '1',
    },
  });
} catch (err) {
  console.warn(`[DB-BOOTSTRAP] Aviso durante la verificación de base de datos: ${err.message}`);
}

console.log(`\n[BACKEND-RUNNER] Ejecutando backend FastAPI con: ${pythonCmd}`);

const child = spawn(pythonCmd, ['main.py'], {
  cwd: backendDir,
  stdio: 'inherit',
});

child.on('exit', (code) => {
  process.exit(code || 0);
});
