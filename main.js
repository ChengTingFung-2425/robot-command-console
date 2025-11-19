const { app, BrowserWindow, ipcMain } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const crypto = require('crypto');

let mainWindow = null;
let pythonProcess = null;
let appToken = null;

// 生成應用生命週期內有效的 token
function generateToken() {
  return crypto.randomBytes(32).toString('hex');
}

// 啟動 Python Flask 服務
function startPythonService() {
  return new Promise((resolve, reject) => {
    const pythonScript = path.join(__dirname, 'flask_service.py');
    
    // 生成 token 並設定環境變數
    appToken = generateToken();
    
    console.log('Starting Python service...');
    console.log('Token generated (first 8 chars):', appToken.substring(0, 8) + '...');
    
    pythonProcess = spawn('python3', [pythonScript], {
      env: { ...process.env, APP_TOKEN: appToken, PORT: '5000' },
      stdio: 'pipe'
    });
    
    pythonProcess.stdout.on('data', (data) => {
      console.log(`[Python] ${data.toString().trim()}`);
      
      // 檢查服務是否已啟動
      if (data.toString().includes('Running on')) {
        console.log('Python service started successfully');
        resolve();
      }
    });
    
    pythonProcess.stderr.on('data', (data) => {
      console.error(`[Python Error] ${data.toString().trim()}`);
    });
    
    pythonProcess.on('error', (error) => {
      console.error('Failed to start Python service:', error);
      reject(error);
    });
    
    pythonProcess.on('exit', (code, signal) => {
      console.log(`Python service exited with code ${code}, signal ${signal}`);
      pythonProcess = null;
    });
    
    // 設定超時
    setTimeout(() => {
      if (pythonProcess && pythonProcess.exitCode === null) {
        resolve(); // 假設已啟動
      }
      // 不再 reject，僅記錄 log（可選）
    }, 5000);
  });
}

// 健康檢查
async function checkHealth() {
  const maxRetries = 10;
  const retryDelay = 1000;
  
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch('http://127.0.0.1:5000/health');
      if (response.ok) {
        const data = await response.json();
        console.log('Health check passed:', data);
        return true;
      }
    } catch (error) {
      console.log(`Health check attempt ${i + 1}/${maxRetries} failed:`, error.message);
    }
    
    if (i < maxRetries - 1) {
      await new Promise(resolve => setTimeout(resolve, retryDelay));
    }
  }
  
  return false;
}

// 創建主視窗
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });
  
  mainWindow.loadFile('renderer/index.html');
  
  // 開發模式下打開 DevTools
  if (process.env.NODE_ENV === 'development') {
    mainWindow.webContents.openDevTools();
  }
  
  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// IPC 處理：獲取 token
ipcMain.handle('get-token', () => {
  return appToken;
});

// 應用啟動
app.whenReady().then(async () => {
  console.log('Electron app ready, starting Python service...');
  
  try {
    await startPythonService();
    const healthy = await checkHealth();
    
    if (!healthy) {
      console.error('Health check failed, but continuing...');
    }
    
    createWindow();
  } catch (error) {
    console.error('Failed to initialize:', error);
    app.quit();
  }
});

// macOS 重新打開視窗
app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

// 關閉時清理
app.on('before-quit', () => {
  console.log('Shutting down Python service...');
  if (pythonProcess) {
    pythonProcess.kill('SIGTERM');
    pythonProcess = null;
  }
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
