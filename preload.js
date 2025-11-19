const { contextBridge, ipcRenderer } = require('electron');

// 暴露安全的 API 給 renderer
contextBridge.exposeInMainWorld('electronAPI', {
  getToken: () => ipcRenderer.invoke('get-token')
});
