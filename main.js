const { app, BrowserWindow, ipcMain } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const crypto = require('crypto');

let mainWindow = null;
let pythonProcess = null;
let appToken = null;
let healthCheckInterval = null;
let healthStatus = 'unknown';

// JSON 結構化日誌函數
function logJSON(level, event, message, extra = {}) {
  const logEntry = {
    timestamp: new Date().toISOString(),
    level: level.toUpperCase(),
    event: event,
    message: message,
    service: 'electron-main',
    ...extra
  };
  console.log(JSON.stringify(logEntry));
}

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
    
    logJSON('info', 'python_service_start', 'Starting Python service', {
      script: pythonScript,
      token_prefix: appToken.substring(0, 8)
    });
    
    pythonProcess = spawn('python3', [pythonScript], {
      env: { ...process.env, APP_TOKEN: appToken, PORT: '5000' },
      stdio: 'pipe'
    });
    
    pythonProcess.stdout.on('data', (data) => {
      // Python 服務現在使用 JSON 日誌，直接輸出
      const output = data.toString().trim();
      console.log(`[Python] ${output}`);
      
      // 檢查服務是否已啟動
      if (output.includes('Running on')) {
        logJSON('info', 'python_service_ready', 'Python service started successfully');
        resolve();
      }
    });
    
    pythonProcess.stderr.on('data', (data) => {
      logJSON('error', 'python_service_error', 'Python service error', {
        error: data.toString().trim()
      });
    });
    
    pythonProcess.on('error', (error) => {
      logJSON('error', 'python_service_spawn_error', 'Failed to start Python service', {
        error: error.message,
        code: error.code
      });
      reject(error);
    });
    
    pythonProcess.on('exit', (code, signal) => {
      logJSON('warn', 'python_service_exit', 'Python service exited', {
        exit_code: code,
        signal: signal
      });
      pythonProcess = null;
    });
    
    // 設定超時
    setTimeout(() => {
      if (pythonProcess && pythonProcess.exitCode === null) {
        logJSON('info', 'python_service_timeout', 'Python service assumed started after timeout');
        resolve(); // 假設已啟動
      }
    }, 5000);
  });
}

// 健康檢查
async function checkHealth() {
  const maxRetries = 10;
  const retryDelay = 1000;
  
  logJSON('info', 'health_check_start', 'Starting health check', {
    max_retries: maxRetries,
    retry_delay_ms: retryDelay
  });
  
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch('http://127.0.0.1:5000/health');
      if (response.ok) {
        const data = await response.json();
        const newStatus = 'healthy';
        
        if (healthStatus !== newStatus) {
          logJSON('info', 'health_status_transition', 'Health status changed', {
            previous_status: healthStatus,
            new_status: newStatus,
            attempt: i + 1
          });
          healthStatus = newStatus;
        }
        
        logJSON('info', 'health_check_success', 'Health check passed', {
          attempt: i + 1,
          response: data
        });
        return true;
      }
    } catch (error) {
      logJSON('warn', 'health_check_attempt_failed', 'Health check attempt failed', {
        attempt: i + 1,
        max_retries: maxRetries,
        error: error.message
      });
    }
    
    if (i < maxRetries - 1) {
      await new Promise(resolve => setTimeout(resolve, retryDelay));
    }
  }
  
  const newStatus = 'unhealthy';
  if (healthStatus !== newStatus) {
    logJSON('error', 'health_status_transition', 'Health status changed', {
      previous_status: healthStatus,
      new_status: newStatus
    });
    healthStatus = newStatus;
  }
  
  logJSON('error', 'health_check_failed', 'All health check attempts failed', {
    total_attempts: maxRetries
  });
  
  return false;
}

// 定期健康檢查
function startPeriodicHealthCheck() {
  if (healthCheckInterval) {
    clearInterval(healthCheckInterval);
  }
  
  logJSON('info', 'periodic_health_check_start', 'Starting periodic health checks', {
    interval_ms: 30000
  });
  
  healthCheckInterval = setInterval(async () => {
    await checkHealth();
  }, 30000); // 每 30 秒檢查一次
}

// 創建主視窗
function createWindow() {
  logJSON('info', 'window_create', 'Creating main window', {
    width: 1200,
    height: 800
  });
  
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
    logJSON('info', 'devtools_open', 'Opening DevTools in development mode');
    mainWindow.webContents.openDevTools();
  }
  
  mainWindow.on('closed', () => {
    logJSON('info', 'window_closed', 'Main window closed');
    mainWindow = null;
  });
  
  logJSON('info', 'window_created', 'Main window created successfully');
}

// IPC 處理：獲取 token
ipcMain.handle('get-token', () => {
  return appToken;
});

// 應用啟動
app.whenReady().then(async () => {
  logJSON('info', 'app_ready', 'Electron app ready, initializing services');
  
  try {
    await startPythonService();
    const healthy = await checkHealth();
    
    if (!healthy) {
      logJSON('warn', 'health_check_initial_fail', 'Initial health check failed, but continuing');
    } else {
      logJSON('info', 'health_check_initial_success', 'Initial health check passed');
    }
    
    createWindow();
    startPeriodicHealthCheck();
    
    logJSON('info', 'app_initialized', 'Application initialized successfully');
  } catch (error) {
    logJSON('error', 'app_init_failed', 'Failed to initialize application', {
      error: error.message,
      stack: error.stack
    });
    app.quit();
  }
});

// macOS 重新打開視窗
app.on('activate', () => {
  logJSON('info', 'app_activate', 'App activated');
  if (BrowserWindow.getAllWindows().length === 0) {
    logJSON('info', 'window_recreate', 'No windows open, creating new window');
    createWindow();
  }
});

// 關閉時清理
app.on('before-quit', () => {
  logJSON('info', 'app_before_quit', 'Application shutting down, cleaning up resources');
  
  if (healthCheckInterval) {
    clearInterval(healthCheckInterval);
    logJSON('info', 'health_check_stopped', 'Stopped periodic health checks');
  }
  
  if (pythonProcess) {
    logJSON('info', 'python_service_shutdown', 'Shutting down Python service');
    pythonProcess.kill('SIGTERM');
    pythonProcess = null;
  }
});

app.on('window-all-closed', () => {
  logJSON('info', 'windows_all_closed', 'All windows closed', {
    platform: process.platform
  });
  
  if (process.platform !== 'darwin') {
    logJSON('info', 'app_quit', 'Quitting application (non-macOS platform)');
    app.quit();
  }
});
