const { app, BrowserWindow, ipcMain, Notification } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const crypto = require('crypto');

let mainWindow = null;
let appToken = null;
let healthCheckInterval = null;

// 服務協調器配置常數
const COORDINATOR_CONFIG = {
  maxRestartAttempts: 3,
  restartDelayMs: 2000,
  alertThreshold: 3,
  healthCheckIntervalMs: 30000,
};

// 服務協調器 - 管理多個服務
const serviceCoordinator = {
  services: {
    flask: {
      name: 'Flask API 服務',
      type: 'python-flask',  // 服務類型，用於決定啟動邏輯
      process: null,
      status: 'stopped',
      port: 5000,
      healthUrl: 'http://127.0.0.1:5000/health',
      startupTimeoutMs: 5000,  // 可配置的啟動超時
      restartAttempts: 0,
      consecutiveFailures: 0,
      lastHealthCheck: null,
      script: null,  // 將在 startService 中設置
    }
  },
  restartInProgress: false,
};

// JSON 結構化日誌函數
function logJSON(level, event, message, extra = {}) {
  const logEntry = {
    timestamp: new Date().toISOString(),
    level: level.toUpperCase(),
    event: event,
    message: message,
    service: 'electron-launcher',
    ...extra
  };
  console.log(JSON.stringify(logEntry));
}

// 告警訊息常數（支援未來國際化擴展）
const ALERT_MESSAGES = {
  SERVICE_RESTART_FAILED: {
    title: '服務重啟失敗',
    bodyTemplate: (name, attempts, max) => `${name} 嘗試 ${attempts}/${max} 次後仍無法重啟`
  },
  SERVICE_FAILURE: {
    title: '服務故障',
    bodyTemplate: (name) => `${name} 已達最大重啟次數，服務無法恢復`
  },
  HEALTH_ABNORMAL: {
    title: '服務健康狀態異常',
    bodyTemplate: (name, failures) => `${name} 已連續 ${failures} 次健康檢查失敗`
  },
  ALL_SERVICES_STARTED: {
    title: '所有服務已啟動',
    body: '統一啟動器已成功啟動所有服務'
  },
  ALL_SERVICES_STOPPED: {
    title: '所有服務已停止',
    body: '統一啟動器已停止所有服務'
  }
};

// 發送系統通知告警
function sendHealthAlert(title, body, context = {}) {
  const alertContext = {
    title: title,
    body: body,
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

// 取得服務狀態摘要
function getServicesStatus() {
  const statuses = {};
  for (const [key, service] of Object.entries(serviceCoordinator.services)) {
    statuses[key] = {
      name: service.name,
      status: service.status,
      port: service.port,
      restartAttempts: service.restartAttempts,
      consecutiveFailures: service.consecutiveFailures,
      lastHealthCheck: service.lastHealthCheck,
      isRunning: service.process !== null,
    };
  }
  return statuses;
}

// 啟動單個服務
async function startService(serviceKey) {
  const service = serviceCoordinator.services[serviceKey];
  if (!service) {
    logJSON('error', 'service_not_found', `Service ${serviceKey} not found`);
    return false;
  }
  
  if (service.process) {
    logJSON('warn', 'service_already_running', `${service.name} already running`);
    return true;
  }
  
  return new Promise((resolve, reject) => {
    // 根據服務類型決定啟動邏輯
    if (service.type === 'python-flask') {
      const pythonScript = path.join(__dirname, '..', 'flask_service.py');
      service.script = pythonScript;
      
      // 生成 token
      if (!appToken) {
        appToken = generateToken();
      }
      
      logJSON('info', 'service_start', `Starting ${service.name}`, {
        script: pythonScript,
        port: service.port,
        token_prefix: appToken.substring(0, 8),
        service_type: service.type
      });
      
      service.process = spawn('python3', [pythonScript], {
        env: { ...process.env, APP_TOKEN: appToken, PORT: String(service.port) },
        stdio: 'pipe'
      });
      
      service.process.stdout.on('data', (data) => {
        const output = data.toString().trim();
        console.log(`[${serviceKey}] ${output}`);
        
        if (output.includes('Running on')) {
          service.status = 'running';
          logJSON('info', 'service_ready', `${service.name} started successfully`);
          resolve(true);
        }
      });
      
      service.process.stderr.on('data', (data) => {
        logJSON('error', 'service_error', `${service.name} error`, {
          service: serviceKey,
          error: data.toString().trim()
        });
      });
      
      service.process.on('error', (error) => {
        service.status = 'error';
        logJSON('error', 'service_spawn_error', `Failed to start ${service.name}`, {
          error: error.message,
          code: error.code
        });
        reject(error);
      });
      
      service.process.on('exit', (code, signal) => {
        logJSON('warn', 'service_exit', `${service.name} exited`, {
          exit_code: code,
          signal: signal
        });
        service.process = null;
        service.status = code === 0 ? 'stopped' : 'error';
        
        // 自動重啟邏輯
        if (code !== 0 && service.restartAttempts < COORDINATOR_CONFIG.maxRestartAttempts && !serviceCoordinator.restartInProgress) {
          service.restartAttempts++;
          logJSON('info', 'service_restart', `Attempting to restart ${service.name}`, {
            attempt: service.restartAttempts,
            max_attempts: COORDINATOR_CONFIG.maxRestartAttempts
          });
          
          setTimeout(async () => {
            try {
              serviceCoordinator.restartInProgress = true;
              await startService(serviceKey);
              const healthy = await checkServiceHealth(serviceKey);
              if (healthy) {
                service.restartAttempts = 0;
                logJSON('info', 'service_restart_success', `${service.name} restarted successfully`);
              }
            } catch (error) {
              sendHealthAlert(
                ALERT_MESSAGES.SERVICE_RESTART_FAILED.title,
                ALERT_MESSAGES.SERVICE_RESTART_FAILED.bodyTemplate(service.name, service.restartAttempts, COORDINATOR_CONFIG.maxRestartAttempts),
                { alertType: 'restart_failed', service: serviceKey }
              );
            } finally {
              serviceCoordinator.restartInProgress = false;
            }
          }, COORDINATOR_CONFIG.restartDelayMs);
        } else if (service.restartAttempts >= COORDINATOR_CONFIG.maxRestartAttempts) {
          sendHealthAlert(
            ALERT_MESSAGES.SERVICE_FAILURE.title,
            ALERT_MESSAGES.SERVICE_FAILURE.bodyTemplate(service.name),
            { alertType: 'service_failure', service: serviceKey }
          );
        }
      });
      
      // 設定超時（使用服務配置的超時時間）
      const startupTimeout = service.startupTimeoutMs || 5000;
      setTimeout(() => {
        if (service.process && service.process.exitCode === null && service.status !== 'running') {
          service.status = 'running';
          logJSON('info', 'service_timeout', `${service.name} assumed started after timeout`, {
            timeout_ms: startupTimeout
          });
          resolve(true);
        }
      }, startupTimeout);
    } else {
      logJSON('error', 'unknown_service_type', `Unknown service type: ${service.type}`);
      reject(new Error(`Unknown service type: ${service.type}`));
    }
  });
}

// 停止單個服務
async function stopService(serviceKey) {
  const service = serviceCoordinator.services[serviceKey];
  if (!service) {
    logJSON('error', 'service_not_found', `Service ${serviceKey} not found`);
    return false;
  }
  
  if (!service.process) {
    logJSON('info', 'service_not_running', `${service.name} is not running`);
    return true;
  }
  
  logJSON('info', 'service_stop', `Stopping ${service.name}`);
  service.process.kill('SIGTERM');
  service.process = null;
  service.status = 'stopped';
  service.restartAttempts = 0;
  service.consecutiveFailures = 0;
  
  return true;
}

// 啟動所有服務
async function startAllServices() {
  logJSON('info', 'all_services_start', 'Starting all services');
  
  const results = {};
  for (const serviceKey of Object.keys(serviceCoordinator.services)) {
    try {
      results[serviceKey] = await startService(serviceKey);
    } catch (error) {
      results[serviceKey] = false;
      logJSON('error', 'service_start_failed', `Failed to start ${serviceKey}`, { error: error.message });
    }
  }
  
  // 執行初始健康檢查
  await checkAllServicesHealth();
  
  const allSuccessful = Object.values(results).every(r => r === true);
  if (allSuccessful) {
    sendHealthAlert(
      ALERT_MESSAGES.ALL_SERVICES_STARTED.title,
      ALERT_MESSAGES.ALL_SERVICES_STARTED.body,
      { alertType: 'all_started' }
    );
  }
  
  return results;
}

// 停止所有服務
async function stopAllServices() {
  logJSON('info', 'all_services_stop', 'Stopping all services');
  
  const results = {};
  for (const serviceKey of Object.keys(serviceCoordinator.services)) {
    results[serviceKey] = await stopService(serviceKey);
  }
  
  return results;
}

// 檢查單個服務健康狀態
async function checkServiceHealth(serviceKey) {
  const service = serviceCoordinator.services[serviceKey];
  if (!service) {
    return false;
  }
  
  const maxRetries = 10;
  const retryDelay = 1000;
  
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch(service.healthUrl);
      if (response.ok) {
        const data = await response.json();
        
        // 重置連續失敗計數
        if (service.consecutiveFailures > 0) {
          logJSON('info', 'health_recovered', `${service.name} health recovered`, {
            previous_failures: service.consecutiveFailures
          });
          service.consecutiveFailures = 0;
        }
        
        service.status = 'healthy';
        service.lastHealthCheck = new Date().toISOString();
        
        logJSON('info', 'health_check_success', `${service.name} health check passed`, {
          attempt: i + 1,
          response: data
        });
        return true;
      }
    } catch (error) {
      logJSON('warn', 'health_check_attempt_failed', `${service.name} health check attempt failed`, {
        attempt: i + 1,
        error: error.message
      });
    }
    
    if (i < maxRetries - 1) {
      await new Promise(resolve => setTimeout(resolve, retryDelay));
    }
  }
  
  service.consecutiveFailures++;
  service.status = 'unhealthy';
  service.lastHealthCheck = new Date().toISOString();
  
  logJSON('error', 'health_check_failed', `${service.name} health check failed`, {
    consecutive_failures: service.consecutiveFailures
  });
  
  // 連續失敗達到閾值時發送告警並嘗試重啟
  if (service.consecutiveFailures >= COORDINATOR_CONFIG.alertThreshold) {
    sendHealthAlert(
      ALERT_MESSAGES.HEALTH_ABNORMAL.title,
      ALERT_MESSAGES.HEALTH_ABNORMAL.bodyTemplate(service.name, service.consecutiveFailures),
      { alertType: 'health_failure', service: serviceKey }
    );
    
    // 嘗試自動重啟
    if (!service.process && service.restartAttempts < COORDINATOR_CONFIG.maxRestartAttempts && !serviceCoordinator.restartInProgress) {
      serviceCoordinator.restartInProgress = true;
      service.restartAttempts++;
      try {
        await startService(serviceKey);
        const healthy = await checkServiceHealth(serviceKey);
        if (healthy) {
          service.restartAttempts = 0;
          service.consecutiveFailures = 0;
        }
      } catch (error) {
        logJSON('error', 'health_restart_failed', `Automatic restart failed for ${service.name}`, {
          error: error.message
        });
      } finally {
        serviceCoordinator.restartInProgress = false;
      }
    }
  }
  
  return false;
}

// 檢查所有服務健康狀態
async function checkAllServicesHealth() {
  const results = {};
  for (const serviceKey of Object.keys(serviceCoordinator.services)) {
    results[serviceKey] = await checkServiceHealth(serviceKey);
  }
  return results;
}

// 定期健康檢查
function startPeriodicHealthCheck() {
  if (healthCheckInterval) {
    clearInterval(healthCheckInterval);
  }
  
  logJSON('info', 'periodic_health_check_start', 'Starting periodic health checks', {
    interval_ms: COORDINATOR_CONFIG.healthCheckIntervalMs
  });
  
  healthCheckInterval = setInterval(async () => {
    await checkAllServicesHealth();
  }, COORDINATOR_CONFIG.healthCheckIntervalMs);
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

// IPC 處理：獲取所有服務狀態
ipcMain.handle('get-services-status', () => {
  return getServicesStatus();
});

// IPC 處理：獲取健康狀態（向後相容）
ipcMain.handle('get-health-status', () => {
  const flask = serviceCoordinator.services.flask;
  return {
    status: flask.status,
    consecutiveFailures: flask.consecutiveFailures,
    restartAttempts: flask.restartAttempts,
    pythonRunning: flask.process !== null
  };
});

// IPC 處理：啟動單個服務
ipcMain.handle('start-service', async (event, serviceKey) => {
  logJSON('info', 'ipc_start_service', `IPC request to start service: ${serviceKey}`);
  try {
    const result = await startService(serviceKey);
    const healthy = await checkServiceHealth(serviceKey);
    return { success: result && healthy, message: healthy ? 'Service started successfully' : 'Service started but health check failed' };
  } catch (error) {
    return { success: false, message: error.message };
  }
});

// IPC 處理：停止單個服務
ipcMain.handle('stop-service', async (event, serviceKey) => {
  logJSON('info', 'ipc_stop_service', `IPC request to stop service: ${serviceKey}`);
  try {
    const result = await stopService(serviceKey);
    return { success: result, message: result ? 'Service stopped successfully' : 'Failed to stop service' };
  } catch (error) {
    return { success: false, message: error.message };
  }
});

// IPC 處理：啟動所有服務
ipcMain.handle('start-all-services', async () => {
  logJSON('info', 'ipc_start_all_services', 'IPC request to start all services');
  try {
    const results = await startAllServices();
    const allSuccessful = Object.values(results).every(r => r === true);
    return { success: allSuccessful, results: results };
  } catch (error) {
    return { success: false, message: error.message };
  }
});

// IPC 處理：停止所有服務
ipcMain.handle('stop-all-services', async () => {
  logJSON('info', 'ipc_stop_all_services', 'IPC request to stop all services');
  try {
    const results = await stopAllServices();
    const allSuccessful = Object.values(results).every(r => r === true);
    return { success: allSuccessful, results: results };
  } catch (error) {
    return { success: false, message: error.message };
  }
});

// IPC 處理：手動重啟 Python 服務（向後相容）
ipcMain.handle('restart-python-service', async () => {
  logJSON('info', 'manual_restart_requested', 'Manual Python service restart requested');
  
  await stopService('flask');
  
  // 重置計數器
  serviceCoordinator.services.flask.restartAttempts = 0;
  serviceCoordinator.services.flask.consecutiveFailures = 0;
  
  try {
    await startService('flask');
    const healthy = await checkServiceHealth('flask');
    return { success: healthy, message: healthy ? 'Service restarted successfully' : 'Service started but health check failed' };
  } catch (error) {
    return { success: false, message: error.message };
  }
});

// IPC 處理：執行健康檢查
ipcMain.handle('check-health', async (event, serviceKey) => {
  logJSON('info', 'ipc_check_health', `IPC request to check health: ${serviceKey || 'all'}`);
  if (serviceKey) {
    const healthy = await checkServiceHealth(serviceKey);
    return { [serviceKey]: healthy };
  } else {
    return await checkAllServicesHealth();
  }
});

// 應用啟動
app.whenReady().then(async () => {
  logJSON('info', 'app_ready', 'Unified Launcher ready, initializing services');
  
  try {
    // 啟動所有服務
    await startAllServices();
    
    createWindow();
    startPeriodicHealthCheck();
    
    logJSON('info', 'app_initialized', 'Unified Launcher initialized successfully');
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
app.on('before-quit', async () => {
  logJSON('info', 'app_before_quit', 'Unified Launcher shutting down, cleaning up resources');
  
  if (healthCheckInterval) {
    clearInterval(healthCheckInterval);
    logJSON('info', 'health_check_stopped', 'Stopped periodic health checks');
  }
  
  // 停止所有服務
  await stopAllServices();
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
