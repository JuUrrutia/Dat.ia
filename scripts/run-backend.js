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

console.log(`[BACKEND-RUNNER] Ejecutando backend con: ${pythonCmd}`);

const child = spawn(pythonCmd, ['main.py'], {
  cwd: backendDir,
  stdio: 'inherit',
});

child.on('exit', (code) => {
  process.exit(code || 0);
});
