const { contextBridge, ipcRenderer } = require('electron');

// 暴露安全的 API 給 renderer
contextBridge.exposeInMainWorld('electronAPI', {
  // 獲取認證 Token
  getToken: () => ipcRenderer.invoke('get-token'),
  
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
