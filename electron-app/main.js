const { app, BrowserWindow, ipcMain, Notification } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const crypto = require('crypto');

let mainWindow = null;
let pythonProcess = null;
let appToken = null;
let healthCheckInterval = null;
let healthStatus = 'unknown';
let restartAttempts = 0;
const MAX_RESTART_ATTEMPTS = 3;
const RESTART_DELAY_MS = 2000;
let consecutiveFailures = 0;
const ALERT_THRESHOLD = 3;  // 連續失敗次數閾值，超過則發送告警
let restartInProgress = false;  // 防止並發重啟

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

// 告警訊息常數（支援未來國際化擴展）
const ALERT_MESSAGES = {
  SERVICE_RESTART_FAILED: {
    title: 'Python 服務重啟失敗',
    bodyTemplate: (attempts, max) => `嘗試 ${attempts}/${max} 次後仍無法重啟`
  },
  SERVICE_FAILURE: {
    title: 'Python 服務故障',
    body: '已達最大重啟次數，服務無法恢復'
  },
  HEALTH_ABNORMAL: {
    title: '服務健康狀態異常',
    bodyTemplate: (failures) => `Python 服務已連續 ${failures} 次健康檢查失敗`
  }
};

// 發送系統通知告警
function sendHealthAlert(title, body, context = {}) {
  const alertContext = {
    title: title,
    body: body,
    consecutive_failures: consecutiveFailures,
    restart_attempts: restartAttempts,
    alert_type: context.alertType || 'unknown',
    ...context
  };
  
  if (Notification.isSupported()) {
    const notification = new Notification({
      title: `Robot Console: ${title}`,
      body: body,
      urgency: 'critical'
    });
    notification.show();
    
    logJSON('warn', 'health_alert_sent', 'Health alert notification sent', alertContext);
  } else {
    logJSON('warn', 'health_alert_unsupported', 'System notifications not supported', alertContext);
  }
}

// 生成應用生命週期內有效的 token
function generateToken() {
  return crypto.randomBytes(32).toString('hex');
}

// 啟動 Python Flask 服務
function startPythonService() {
  return new Promise((resolve, reject) => {
    const pythonScript = path.join(__dirname, '..', 'flask_service.py');
    
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
      
      // 自動重啟邏輯（僅在非正常退出且未超過重試次數時）
      if (code !== 0 && restartAttempts < MAX_RESTART_ATTEMPTS) {
        restartAttempts++;
        logJSON('info', 'python_service_restart', 'Attempting to restart Python service', {
          attempt: restartAttempts,
          max_attempts: MAX_RESTART_ATTEMPTS,
          delay_ms: RESTART_DELAY_MS
        });
        
        setTimeout(async () => {
          try {
            await startPythonService();
            const healthy = await checkHealth();
            if (healthy) {
              logJSON('info', 'python_service_restart_success', 'Python service restarted successfully');
              restartAttempts = 0;  // 重置重啟計數
            }
          } catch (error) {
            logJSON('error', 'python_service_restart_failed', 'Failed to restart Python service', {
              error: error.message
            });
            sendHealthAlert(
              ALERT_MESSAGES.SERVICE_RESTART_FAILED.title,
              ALERT_MESSAGES.SERVICE_RESTART_FAILED.bodyTemplate(restartAttempts, MAX_RESTART_ATTEMPTS),
              { alertType: 'restart_failed' }
            );
          }
        }, RESTART_DELAY_MS);
      } else if (restartAttempts >= MAX_RESTART_ATTEMPTS) {
        logJSON('error', 'python_service_restart_exhausted', 'Max restart attempts reached', {
          attempts: restartAttempts
        });
        sendHealthAlert(
          ALERT_MESSAGES.SERVICE_FAILURE.title,
          ALERT_MESSAGES.SERVICE_FAILURE.body,
          { alertType: 'service_failure' }
        );
      }
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
        
        // 重置連續失敗計數
        if (consecutiveFailures > 0) {
          logJSON('info', 'health_recovered', 'Health check recovered after failures', {
            previous_failures: consecutiveFailures
          });
          consecutiveFailures = 0;
        }
        
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
  consecutiveFailures++;
  
  if (healthStatus !== newStatus) {
    logJSON('error', 'health_status_transition', 'Health status changed', {
      previous_status: healthStatus,
      new_status: newStatus,
      consecutive_failures: consecutiveFailures
    });
    healthStatus = newStatus;
  }
  
  logJSON('error', 'health_check_failed', 'All health check attempts failed', {
    total_attempts: maxRetries,
    consecutive_failures: consecutiveFailures
  });
  
  // 連續失敗達到閾值時發送告警
  if (consecutiveFailures >= ALERT_THRESHOLD) {
    sendHealthAlert(
      ALERT_MESSAGES.HEALTH_ABNORMAL.title,
      ALERT_MESSAGES.HEALTH_ABNORMAL.bodyTemplate(consecutiveFailures),
      { alertType: 'health_failure' }
    );
    
    // 嘗試自動重啟（防止並發重啟）
    if (!pythonProcess && restartAttempts < MAX_RESTART_ATTEMPTS && !restartInProgress) {
      restartInProgress = true;
      logJSON('info', 'health_triggered_restart', 'Health check triggered automatic restart');
      restartAttempts++;
      try {
        await startPythonService();
        const healthy = await checkHealth();
        if (healthy) {
          logJSON('info', 'health_restart_success', 'Automatic restart successful');
          restartAttempts = 0;
          consecutiveFailures = 0;
        }
      } catch (error) {
        logJSON('error', 'health_restart_failed', 'Automatic restart failed', {
          error: error.message
        });
      } finally {
        restartInProgress = false;
      }
    }
  }
  
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

// IPC 處理：獲取健康狀態
ipcMain.handle('get-health-status', () => {
  return {
    status: healthStatus,
    consecutiveFailures: consecutiveFailures,
    restartAttempts: restartAttempts,
    pythonRunning: pythonProcess !== null
  };
});

// IPC 處理：手動重啟 Python 服務
ipcMain.handle('restart-python-service', async () => {
  logJSON('info', 'manual_restart_requested', 'Manual Python service restart requested');
  
  if (pythonProcess) {
    pythonProcess.kill('SIGTERM');
    pythonProcess = null;
  }
  
  // 重置計數器
  restartAttempts = 0;
  consecutiveFailures = 0;
  
  try {
    await startPythonService();
    const healthy = await checkHealth();
    return { success: healthy, message: healthy ? 'Service restarted successfully' : 'Service started but health check failed' };
  } catch (error) {
    return { success: false, message: error.message };
  }
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
