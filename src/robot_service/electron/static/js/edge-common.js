/**
 * Edge UI 通用 JavaScript
 * 提供 Edge App 的共用功能
 */

// API 基礎 URL（使用當前 origin，確保在不同部署環境中正常工作）
const API_BASE_URL = window.location.origin;

/**
 * 通用 API 請求函式
 * @param {string} endpoint - API 端點路徑
 * @param {Object} options - fetch 選項
 * @returns {Promise<Object>} API 回應資料
 * @throws {Error} 當請求失敗或回應不正常時拋出錯誤
 */
async function apiRequest(endpoint, options = {}) {
    const url = API_BASE_URL + endpoint;
    
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
    };
    
    const mergedOptions = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers,
        },
    };
    
    try {
        const response = await fetch(url, mergedOptions);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || `HTTP ${response.status}`);
        }
        
        return data;
    } catch (error) {
        console.error(`API request failed: ${endpoint}`, error);
        throw error;
    }
}

/**
 * 更新連線狀態指示器
 * @returns {Promise<void>}
 */
async function updateConnectionStatus() {
    try {
        const data = await apiRequest('/api/edge/llm/status');
        const indicator = document.getElementById('connection-status');
        
        if (!indicator) return;
        
        if (data.local_llm_available && data.internet_available) {
            indicator.textContent = '✅ 完全連線';
            indicator.className = 'status-indicator status-success';
        } else if (data.local_llm_available || data.internet_available) {
            indicator.textContent = '⚠️ 部分連線';
            indicator.className = 'status-indicator status-warning';
        } else {
            indicator.textContent = '❌ 離線模式';
            indicator.className = 'status-indicator status-error';
        }
    } catch (error) {
        const indicator = document.getElementById('connection-status');
        if (indicator) {
            indicator.textContent = '❓ 狀態未知';
            indicator.className = 'status-indicator status-checking';
        }
    }
}

/**
 * 格式化時間
 * @param {Date|string} date - 日期物件或 ISO 字串
 * @returns {string} 格式化的時間字串
 */
function formatTime(date) {
    if (typeof date === 'string') {
        date = new Date(date);
    }
    return date.toLocaleTimeString('zh-TW', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
    });
}

/**
 * 格式化日期時間
 * @param {Date|string} date - 日期物件或 ISO 字串
 * @returns {string} 格式化的日期時間字串
 */
function formatDateTime(date) {
    if (typeof date === 'string') {
        date = new Date(date);
    }
    return date.toLocaleString('zh-TW', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
    });
}

/**
 * 顯示提示訊息（Toast 通知）
 * @param {string} message - 訊息內容
 * @param {string} type - 訊息類型 ('success' | 'error' | 'warning' | 'info')
 * @param {number} duration - 顯示時間（毫秒）
 */
function showToast(message, type = 'success', duration = 3000) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    // 添加 ARIA 屬性以提升可訪問性
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'polite');
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, duration);
}

/**
 * 確認對話框
 * @param {string} message - 確認訊息
 * @returns {Promise<boolean>} 用戶選擇結果
 */
function confirmAction(message) {
    return new Promise((resolve) => {
        resolve(window.confirm(message));
    });
}

// 頁面載入時初始化
document.addEventListener('DOMContentLoaded', function() {
    // 更新連線狀態
    updateConnectionStatus();
    
    // 定期更新連線狀態（每 30 秒）
    setInterval(updateConnectionStatus, 30000);
});

// 匯出函式供其他腳本使用
window.EdgeUI = {
    apiRequest,
    updateConnectionStatus,
    formatTime,
    formatDateTime,
    showToast,
    confirmAction,
};
