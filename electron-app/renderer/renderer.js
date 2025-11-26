// Renderer process JavaScript - 統一啟動器

const API_BASE_URL = 'http://127.0.0.1:5000';
let appToken = null;
let servicesStatus = {};
let refreshInterval = null;

// 服務名稱對照表
const SERVICE_DISPLAY_NAMES = {
    flask: {
        name: 'Flask API 服務',
        icon: '🔌',
        description: 'HTTP REST API 服務，提供機器人控制介面'
    }
};

// 狀態顯示對照表
const STATUS_LABELS = {
    running: '運行中',
    healthy: '健康',
    stopped: '已停止',
    error: '錯誤',
    unhealthy: '異常',
    unknown: '未知'
};

// 初始化
async function initialize() {
    console.log('統一啟動器初始化中...');
    
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
    
    // 獲取服務狀態
    await refreshServicesStatus();
    
    // 設置自動刷新（每 10 秒）
    refreshInterval = setInterval(refreshServicesStatus, 10000);
    
    // 綁定事件
    bindEventListeners();
}

// 綁定事件監聽器
function bindEventListeners() {
    // 啟動所有服務
    document.getElementById('start-all-btn').addEventListener('click', async () => {
        const btn = document.getElementById('start-all-btn');
        btn.disabled = true;
        btn.textContent = '⏳ 啟動中...';
        
        try {
            const result = await window.electronAPI.startAllServices();
            console.log('Start all services result:', result);
            await refreshServicesStatus();
        } catch (error) {
            console.error('Failed to start services:', error);
        } finally {
            btn.disabled = false;
            btn.textContent = '▶️ 啟動所有服務';
        }
    });
    
    // 停止所有服務
    document.getElementById('stop-all-btn').addEventListener('click', async () => {
        const btn = document.getElementById('stop-all-btn');
        btn.disabled = true;
        btn.textContent = '⏳ 停止中...';
        
        try {
            const result = await window.electronAPI.stopAllServices();
            console.log('Stop all services result:', result);
            await refreshServicesStatus();
        } catch (error) {
            console.error('Failed to stop services:', error);
        } finally {
            btn.disabled = false;
            btn.textContent = '⏹️ 停止所有服務';
        }
    });
    
    // 刷新狀態
    document.getElementById('refresh-status-btn').addEventListener('click', async () => {
        const btn = document.getElementById('refresh-status-btn');
        btn.disabled = true;
        btn.textContent = '⏳ 刷新中...';
        
        await refreshServicesStatus();
        
        btn.disabled = false;
        btn.textContent = '🔄 重新整理狀態';
    });
    
    // 健康檢查
    document.getElementById('test-health').addEventListener('click', checkAllServicesHealth);
    
    // API ping 測試
    document.getElementById('test-ping').addEventListener('click', testPing);
}

// 刷新服務狀態
async function refreshServicesStatus() {
    try {
        servicesStatus = await window.electronAPI.getServicesStatus();
        console.log('Services status:', servicesStatus);
        
        renderServicesDashboard(servicesStatus);
        updateOverallHealthStatus(servicesStatus);
        
        // 更新最後更新時間
        document.getElementById('last-update-time').textContent = new Date().toLocaleTimeString();
    } catch (error) {
        console.error('Failed to get services status:', error);
    }
}

// 渲染服務儀表板
function renderServicesDashboard(services) {
    const dashboard = document.getElementById('services-dashboard');
    dashboard.innerHTML = '';
    
    for (const [key, service] of Object.entries(services)) {
        const displayInfo = SERVICE_DISPLAY_NAMES[key] || { name: key, icon: '📦', description: '' };
        const statusClass = getStatusClass(service.status);
        const statusLabel = STATUS_LABELS[service.status] || service.status;
        
        const card = document.createElement('div');
        card.className = `service-card ${statusClass}`;
        card.innerHTML = `
            <h3>
                ${displayInfo.icon} ${displayInfo.name}
                <span class="service-status ${statusClass}">${statusLabel}</span>
            </h3>
            <div class="service-info">
                <p>📍 端口: ${service.port}</p>
                <p>🔄 重啟次數: ${service.restartAttempts}</p>
                <p>❌ 連續失敗: ${service.consecutiveFailures}</p>
                <p>⏰ 最後檢查: ${service.lastHealthCheck ? new Date(service.lastHealthCheck).toLocaleTimeString() : '-'}</p>
            </div>
            <div class="service-actions">
                <button class="btn-sm btn-success" onclick="LauncherServices.startService('${key}')" ${service.isRunning ? 'disabled' : ''}>
                    ▶️ 啟動
                </button>
                <button class="btn-sm btn-danger" onclick="LauncherServices.stopService('${key}')" ${!service.isRunning ? 'disabled' : ''}>
                    ⏹️ 停止
                </button>
                <button class="btn-sm" onclick="LauncherServices.checkServiceHealth('${key}')">
                    🔍 檢查
                </button>
            </div>
        `;
        dashboard.appendChild(card);
    }
}

// 獲取狀態對應的 CSS 類別
function getStatusClass(status) {
    switch (status) {
        case 'running':
        case 'healthy':
            return 'healthy';
        case 'stopped':
            return 'stopped';
        case 'error':
            return 'error';
        case 'unhealthy':
            return 'unhealthy';
        default:
            return 'unknown';
    }
}

// 更新整體健康狀態
function updateOverallHealthStatus(services) {
    const statusEl = document.getElementById('health-status');
    
    const allHealthy = Object.values(services).every(s => 
        s.status === 'healthy' || s.status === 'running'
    );
    const anyError = Object.values(services).some(s => 
        s.status === 'error' || s.status === 'unhealthy'
    );
    const allStopped = Object.values(services).every(s => s.status === 'stopped');
    
    if (allStopped) {
        statusEl.className = 'status pending';
        statusEl.innerHTML = '<span class="status-dot"></span><span>⏸️ 所有服務已停止</span>';
    } else if (allHealthy) {
        statusEl.className = 'status success';
        statusEl.innerHTML = '<span class="status-dot"></span><span>✅ 所有服務運行正常</span>';
    } else if (anyError) {
        statusEl.className = 'status error';
        statusEl.innerHTML = '<span class="status-dot"></span><span>❌ 部分服務異常</span>';
    } else {
        statusEl.className = 'status pending';
        statusEl.innerHTML = '<span class="status-dot"></span><span>⏳ 服務狀態檢查中...</span>';
    }
}

// 啟動單個服務
async function startService(serviceKey) {
    console.log('Starting service:', serviceKey);
    try {
        const result = await window.electronAPI.startService(serviceKey);
        console.log('Start service result:', result);
        await refreshServicesStatus();
    } catch (error) {
        console.error('Failed to start service:', error);
    }
}

// 停止單個服務
async function stopService(serviceKey) {
    console.log('Stopping service:', serviceKey);
    try {
        const result = await window.electronAPI.stopService(serviceKey);
        console.log('Stop service result:', result);
        await refreshServicesStatus();
    } catch (error) {
        console.error('Failed to stop service:', error);
    }
}

// 檢查單個服務健康狀態
async function checkServiceHealth(serviceKey) {
    console.log('Checking service health:', serviceKey);
    try {
        const result = await window.electronAPI.checkHealth(serviceKey);
        console.log('Health check result:', result);
        await refreshServicesStatus();
    } catch (error) {
        console.error('Failed to check health:', error);
    }
}

// 檢查所有服務健康狀態
async function checkAllServicesHealth() {
    const resultEl = document.getElementById('health-result');
    resultEl.textContent = '檢查中...';
    resultEl.style.display = 'block';
    
    try {
        const result = await window.electronAPI.checkHealth();
        console.log('All services health check result:', result);
        
        // 顯示結果
        const healthInfo = {};
        for (const [key, healthy] of Object.entries(result)) {
            healthInfo[key] = healthy ? '✅ 健康' : '❌ 異常';
        }
        
        resultEl.textContent = JSON.stringify(healthInfo, null, 2);
        await refreshServicesStatus();
    } catch (error) {
        console.error('Failed to check all services health:', error);
        resultEl.textContent = `❌ 檢查失敗: ${error.message}`;
    }
}

// 測試 ping 端點
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

// 全域命名空間供 HTML onclick 使用
window.LauncherServices = {
    startService: startService,
    stopService: stopService,
    checkServiceHealth: checkServiceHealth
};

// 啟動時初始化
initialize();
