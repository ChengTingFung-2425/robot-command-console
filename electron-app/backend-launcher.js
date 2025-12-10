/**
 * 後端服務啟動器（Node.js 包裝）
 * 呼叫 Python 的 BackendServiceManager 來啟動所有後端服務
 * 
 * 這個模組隱藏了所有底層細節，提供簡單的啟動/停止介面
 */

const { spawn } = require('child_process');
const path = require('path');

class BackendLauncher {
  constructor(debugMode = false) {
    // 秘密除錯模式檢測（開發者專用）
    this.debugMode = this._checkSecretDebugMode() || debugMode;
    this.pythonProcess = null;
    this.serviceInfo = null;
    this.ready = false;
  }

  /**
   * 檢查秘密除錯模式（開發者專用）
   * 必須同時滿足以下三個條件：
   * 1. 環境變數: __ROBOT_INTERNAL_DEBUG__=1
   * 2. 檔案標記: .robot_debug 存在
   * 3. 特殊埠號: DEBUG_PORT=54321
   */
  _checkSecretDebugMode() {
    const fs = require('fs');
    const path = require('path');
    
    // 檢查方法 1: 特殊環境變數
    const hasEnvVar = process.env.__ROBOT_INTERNAL_DEBUG__ === '1';
    
    // 檢查方法 2: 隱藏檔案標記
    const debugFile = path.join(__dirname, '..', '.robot_debug');
    const hasDebugFile = fs.existsSync(debugFile);
    
    // 檢查方法 3: 特殊埠號組合
    const hasDebugPort = process.env.DEBUG_PORT === '54321';
    
    // 必須三個條件同時滿足
    return hasEnvVar && hasDebugFile && hasDebugPort;
  }

  /**
   * 啟動所有後端服務
   * @returns {Promise<{success: boolean, flask_url: string, mcp_url: string, token: string}>}
   */
  async start() {
    return new Promise((resolve, reject) => {
      const projectRoot = path.join(__dirname, '..');
      const launcherScript = path.join(projectRoot, 'src', 'common', 'backend_service_manager.py');
      
      // 準備啟動參數
      const args = [launcherScript];
      if (this.debugMode) {
        args.push('--debug');
      }
      
      if (this.debugMode) {
        console.log('[BackendLauncher] Internal diagnostics enabled');
      }
      
      // 啟動 Python 服務管理器
      this.pythonProcess = spawn('python3', args, {
        cwd: projectRoot,
        stdio: this.debugMode ? 'inherit' : 'pipe',
        env: { ...process.env }
      });
      
      let startupBuffer = '';
      let started = false;
      
      // 監聽輸出以偵測啟動完成
      if (!this.debugMode) {
        this.pythonProcess.stdout.on('data', (data) => {
          startupBuffer += data.toString();
          
          // 偵測啟動完成訊息
          if (!started && startupBuffer.includes('所有後端服務已就緒')) {
            started = true;
            this.ready = true;
            
            // 解析服務資訊（簡化版，實際應該透過 IPC 或檔案通訊）
            this.serviceInfo = {
              flask_url: 'http://127.0.0.1:5000',
              mcp_url: 'http://127.0.0.1:8000',
              token: null  // Token 應該透過安全管道傳遞
            };
            
            resolve({
              success: true,
              ...this.serviceInfo
            });
          }
        });
        
        this.pythonProcess.stderr.on('data', (data) => {
          if (this.debugMode) {
            console.error('[BackendLauncher] Error:', data.toString());
          }
        });
      } else {
        // 除錯模式：等待一段時間後假設成功
        setTimeout(() => {
          this.ready = true;
          this.serviceInfo = {
            flask_url: 'http://127.0.0.1:5000',
            mcp_url: 'http://127.0.0.1:8000',
            token: null
          };
          resolve({
            success: true,
            ...this.serviceInfo
          });
        }, 8000);  // 等待 8 秒讓服務啟動
      }
      
      this.pythonProcess.on('error', (error) => {
        console.error('[BackendLauncher] Startup failed:', error);
        reject(error);
      });
      
      this.pythonProcess.on('exit', (code) => {
        if (this.debugMode) {
          console.log('[BackendLauncher] Process exited with code:', code);
        }
        this.ready = false;
        this.pythonProcess = null;
      });
      
      // 超時保護
      setTimeout(() => {
        if (!started && !this.debugMode) {
          reject(new Error('後端服務啟動超時'));
        }
      }, 30000);  // 30 秒超時
    });
  }

  /**
   * 停止所有後端服務
   */
  stop() {
    if (this.pythonProcess) {
      if (this.debugMode) {
        console.log('[BackendLauncher] Stopping backend services...');
      }
      
      this.pythonProcess.kill('SIGTERM');
      
      // 等待 5 秒，如果還沒停止就強制終止
      setTimeout(() => {
        if (this.pythonProcess && this.pythonProcess.pid) {
          this.pythonProcess.kill('SIGKILL');
        }
      }, 5000);
      
      this.pythonProcess = null;
      this.ready = false;
    }
  }

  /**
   * 檢查服務是否就緒
   */
  isReady() {
    return this.ready;
  }

  /**
   * 取得服務資訊
   */
  getServiceInfo() {
    return this.serviceInfo;
  }
}

module.exports = BackendLauncher;
