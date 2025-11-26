const { contextBridge, ipcRenderer } = require('electron');

// 暴露安全的 API 給 renderer
contextBridge.exposeInMainWorld('electronAPI', {
  // 獲取認證 Token
  getToken: () => ipcRenderer.invoke('get-token'),
  
  // 獲取健康狀態
  getHealthStatus: () => ipcRenderer.invoke('get-health-status'),
  
  // 手動重啟 Python 服務
  restartPythonService: () => ipcRenderer.invoke('restart-python-service')
});
