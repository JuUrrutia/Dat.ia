const { spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');

function pythonEnv(extra = {}) {
  const env = { ...process.env };
  delete env.PYTHONHOME;
  delete env.PYTHONPATH;
  delete env.VIRTUAL_ENV;
  return { ...env, ...extra };
}

function isUsableBackendPython(command, backendDir) {
  const result = spawnSync(command, ['-c', 'import fastapi, sqlalchemy, uvicorn, sys; print(sys.executable)'], {
    cwd: backendDir,
    env: pythonEnv(),
    encoding: 'utf-8',
  });
  if (result.status === 0) return result.stdout.trim().split(/\r?\n/).at(-1);

  const output = (result.stderr || result.stdout || `exit code ${result.status}`).trim();
  const reason = result.error?.message || output.split(/\r?\n/).filter(Boolean).at(-1);
  console.warn(`[PYTHON] Ignorando intérprete sin dependencias utilizables ${command}: ${reason}`);
  return null;
}

module.exports = function findPython(backendDir) {
  const candidates = [
    path.join(backendDir, 'venv', 'Scripts', 'python.exe'),
    path.join(backendDir, '.venv', 'Scripts', 'python.exe'),
    path.join(backendDir, '..', '.venv', 'Scripts', 'python.exe'),
    path.join(backendDir, 'venv', 'bin', 'python'),
    path.join(backendDir, '.venv', 'bin', 'python'),
    path.join(backendDir, '..', '.venv', 'bin', 'python'),
  ];

  for (const candidate of candidates) {
    if (!fs.existsSync(candidate)) continue;

    const executable = isUsableBackendPython(candidate, backendDir);
    if (executable) return executable;
  }

  const commands = process.platform === 'win32'
    ? ['python', 'py', 'python3']
    : ['python3', 'python'];

  for (const command of commands) {
    const executable = isUsableBackendPython(command, backendDir);
    if (executable) return executable;
  }

  return null;
};

module.exports.pythonEnv = pythonEnv;
