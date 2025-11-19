// Renderer process JavaScript

const API_BASE_URL = 'http://127.0.0.1:5000';
let appToken = null;

// 初始化
async function initialize() {
    console.log('Renderer initializing...');
    
    // 從 main process 獲取 token
    try {
        appToken = await window.electronAPI.getToken();
        console.log('Token received:', appToken ? appToken.substring(0, 8) + '...' : 'null');
        
        document.getElementById('token-display').textContent = 
            appToken ? appToken.substring(0, 8) + '...' : 'Not available';
        
        if (appToken) {
            document.getElementById('test-ping').disabled = false;
        }
    } catch (error) {
        console.error('Failed to get token:', error);
        document.getElementById('token-display').textContent = 'Error loading';
    }
    
    // 執行初始健康檢查
    await checkHealth();
}

// 健康檢查
async function checkHealth() {
    const statusEl = document.getElementById('health-status');
    const resultEl = document.getElementById('health-result');
    
    statusEl.className = 'status pending';
    statusEl.innerHTML = '<span class="status-dot"></span><span>檢查中...</span>';
    
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        const data = await response.json();
        
        if (response.ok) {
            statusEl.className = 'status success';
            statusEl.innerHTML = '<span class="status-dot"></span><span>✅ 服務運行正常</span>';
            resultEl.textContent = JSON.stringify(data, null, 2);
            resultEl.style.display = 'block';
        } else {
            throw new Error(`HTTP ${response.status}`);
        }
    } catch (error) {
        console.error('Health check failed:', error);
        statusEl.className = 'status error';
        statusEl.innerHTML = '<span class="status-dot"></span><span>❌ 服務無法連接</span>';
        resultEl.textContent = `錯誤: ${error.message}`;
        resultEl.style.display = 'block';
    }
}

// 測試 ping 端點（需要認證）
async function testPing() {
    const resultEl = document.getElementById('ping-result');
    const button = document.getElementById('test-ping');
    
    button.disabled = true;
    resultEl.textContent = '發送請求中...';
    resultEl.style.display = 'block';
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/ping`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${appToken}`,
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (response.ok) {
            resultEl.textContent = `✅ 成功！\n\n${JSON.stringify(data, null, 2)}`;
        } else {
            resultEl.textContent = `❌ 錯誤 ${response.status}\n\n${JSON.stringify(data, null, 2)}`;
        }
    } catch (error) {
        console.error('Ping test failed:', error);
        resultEl.textContent = `❌ 請求失敗: ${error.message}`;
    } finally {
        button.disabled = false;
    }
}

// 事件監聽
document.getElementById('test-health').addEventListener('click', checkHealth);
document.getElementById('test-ping').addEventListener('click', testPing);

// 啟動時初始化
initialize();
