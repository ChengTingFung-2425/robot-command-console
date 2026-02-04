const { contextBridge, ipcRenderer } = require('electron');

// 暴露安全的 API 給 renderer
contextBridge.exposeInMainWorld('electronAPI', {
  // ========== 認證 Token ==========
  
  // 獲取認證 Token
  getToken: () => ipcRenderer.invoke('get-token'),
  
  // 獲取 Token 詳細資訊
  getTokenInfo: () => ipcRenderer.invoke('get-token-info'),
  
  // 輪替 Token
  rotateToken: (reason) => ipcRenderer.invoke('rotate-token', reason),
  
  // 獲取 Token 管理器狀態
  getTokenStatus: () => ipcRenderer.invoke('get-token-status'),
  
  // 獲取 Token 輪替歷史
  getTokenRotationHistory: () => ipcRenderer.invoke('get-token-rotation-history'),
  
  // 檢查是否需要 Token 輪替
  isTokenRotationNeeded: (thresholdHours) => ipcRenderer.invoke('is-token-rotation-needed', thresholdHours),
  
  // 使 Token 失效（安全事件時使用）
  invalidateToken: () => ipcRenderer.invoke('invalidate-token'),
  
  // 監聽 Token 輪替事件
  onTokenRotated: (callback) => {
    ipcRenderer.on('token-rotated', (event, data) => callback(data));
  },
  
  // ========== 服務管理 ==========
  
  // 獲取所有服務狀態
  getServicesStatus: () => ipcRenderer.invoke('get-services-status'),
  
  // 獲取健康狀態（向後相容）
  getHealthStatus: () => ipcRenderer.invoke('get-health-status'),
  
  // 啟動單個服務
  startService: (serviceKey) => ipcRenderer.invoke('start-service', serviceKey),
  
  // 停止單個服務
  stopService: (serviceKey) => ipcRenderer.invoke('stop-service', serviceKey),
  
  // 啟動所有服務
  startAllServices: () => ipcRenderer.invoke('start-all-services'),
  
  // 停止所有服務
  stopAllServices: () => ipcRenderer.invoke('stop-all-services'),
  
  // 手動重啟 Python 服務（向後相容）
  restartPythonService: () => ipcRenderer.invoke('restart-python-service'),
  
  // 執行健康檢查
  checkHealth: (serviceKey) => ipcRenderer.invoke('check-health', serviceKey)
});
