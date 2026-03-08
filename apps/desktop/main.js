const { app, BrowserWindow } = require('electron');
const { spawn } = require('child_process');
const http = require('http');
const path = require('path');
const os = require('os');

let backend;

function waitHttp(url, maxMs = 12000) {
  const start = Date.now();
  return new Promise((resolve, reject) => {
    (function ping() {
      http
        .get(url, (res) => {
          if (res.statusCode && res.statusCode < 500) resolve();
          else retry();
        })
        .on('error', retry);
      function retry() {
        if (Date.now() - start > maxMs) reject(new Error(`timeout: ${url}`));
        else setTimeout(ping, 400);
      }
    })();
  });
}

function getPythonPath(repoRoot) {
  if (os.platform() === 'win32') {
    return path.join(repoRoot, '.venv', 'Scripts', 'python.exe');
  }
  return path.join(repoRoot, '.venv', 'bin', 'python');
}

async function ensureBackend() {
  try {
    await waitHttp('http://127.0.0.1:8000/health', 1500);
    return;
  } catch (_) {
    // backend not running; start local dev backend with .venv python
  }
  const repoRoot = path.join(__dirname, '..', '..');
  const py = getPythonPath(repoRoot);
  backend = spawn(py, ['-m', 'uvicorn', 'apps.backend.app.main:app', '--port', '8000'], {
    cwd: repoRoot,
    stdio: 'inherit',
  });
  await waitHttp('http://127.0.0.1:8000/health', 12000);
}

async function createWindow() {
  await ensureBackend();

  const isDev = !app.isPackaged;
  const win = new BrowserWindow({
    width: 1280,
    height: 900,
    autoHideMenuBar: true,
    webPreferences: {
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
  });

  // Enable Web Speech API (TTS)
  win.webContents.session.setPermissionRequestHandler((_wc, permission, callback) => {
    callback(true); // allow all — local app, no risk
  });

  if (isDev) {
    // Dev: load from Vite dev server
    await waitHttp('http://127.0.0.1:5173', 12000);
    win.loadURL('http://127.0.0.1:5173');
    win.webContents.openDevTools();
  } else {
    // Prod: load built index.html
    const indexPath = path.join(__dirname, '..', 'frontend', 'dist', 'index.html');
    win.loadFile(indexPath);
  }
}

app.whenReady().then(createWindow).catch((err) => {
  console.error('[desktop] startup failed', err);
  app.quit();
});

app.on('before-quit', () => {
  if (backend) backend.kill('SIGTERM');
});
