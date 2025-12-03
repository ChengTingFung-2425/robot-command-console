/**
 * Token 管理器模組
 * 提供 Electron 與背景服務間的安全 Token 管理功能
 * 
 * 功能：
 * - Token 生成與驗證
 * - Token 輪替支援（不中斷服務）
 * - Token 過期管理
 * - Token 資訊查詢
 * - 輪替事件通知
 */

const crypto = require('crypto');

/**
 * Token 資訊
 * @typedef {Object} TokenInfo
 * @property {string} tokenId - Token 識別碼
 * @property {Date} createdAt - 建立時間
 * @property {Date|null} expiresAt - 過期時間
 * @property {boolean} isActive - 是否啟用
 * @property {number} rotationCount - 輪替次數
 */

/**
 * Token 輪替事件
 * @typedef {Object} TokenRotationEvent
 * @property {string|null} oldTokenId - 舊 Token ID
 * @property {string} newTokenId - 新 Token ID
 * @property {Date} timestamp - 時間戳記
 * @property {string} reason - 輪替原因
 */

/**
 * Token 管理器
 * 
 * 提供安全的 Token 生命週期管理：
 * - 生成加密安全的 Token
 * - Token 驗證
 * - Token 輪替（不中斷服務）
 * - Token 過期管理
 * - 輪替事件通知
 */
class TokenManager {
  /**
   * 初始化 Token 管理器
   * @param {Object} options - 配置選項
   * @param {number} [options.tokenLength=32] - Token 長度（bytes）
   * @param {number|null} [options.tokenExpiryHours=null] - Token 有效時間（小時）
   * @param {number} [options.gracePeriodSeconds=60] - 輪替後舊 Token 的寬限期（秒）
   * @param {number} [options.maxRotationHistory=10] - 保留的輪替歷史記錄數
   */
  constructor(options = {}) {
    this.tokenLength = options.tokenLength || 32;
    this.tokenExpiryHours = options.tokenExpiryHours || null;
    this.gracePeriodSeconds = options.gracePeriodSeconds || 60;
    this.maxRotationHistory = options.maxRotationHistory || 10;

    this.currentToken = null;
    this.currentInfo = null;
    this.previousTokens = new Map(); // tokenHash -> TokenInfo
    this.rotationHistory = [];
    this.rotationCallbacks = [];
    this.rotationCount = 0;

    this._log('info', 'token_manager_init', 'TokenManager initialized', {
      tokenLength: this.tokenLength,
      tokenExpiryHours: this.tokenExpiryHours,
      gracePeriodSeconds: this.gracePeriodSeconds,
    });
  }

  /**
   * 結構化日誌輸出
   * @private
   */
  _log(level, event, message, extra = {}) {
    const logEntry = {
      timestamp: new Date().toISOString(),
      level: level.toUpperCase(),
      event: event,
      message: message,
      service: 'electron-token-manager',
      ...extra,
    };
    console.log(JSON.stringify(logEntry));
  }

  /**
   * 生成唯一的 Token ID
   * @private
   */
  _generateTokenId() {
    return crypto.randomBytes(8).toString('hex');
  }

  /**
   * 計算 Token 過期時間
   * @private
   */
  _calculateExpiry() {
    if (this.tokenExpiryHours === null) {
      return null;
    }
    const expiry = new Date();
    expiry.setHours(expiry.getHours() + this.tokenExpiryHours);
    return expiry;
  }

  /**
   * 對 Token 進行雜湊
   * @private
   */
  _hashToken(token) {
    return crypto.createHash('sha256').update(token).digest('hex');
  }

  /**
   * 檢查 TokenInfo 是否已過期
   * @private
   */
  _isExpired(info) {
    if (!info || !info.expiresAt) {
      return false;
    }
    return new Date() > info.expiresAt;
  }

  /**
   * 將當前 Token 歸檔到寬限期列表
   * @private
   */
  _archiveCurrentToken() {
    if (!this.currentToken || !this.currentInfo) {
      return;
    }

    // 設定寬限期過期時間
    const graceExpiry = new Date();
    graceExpiry.setSeconds(graceExpiry.getSeconds() + this.gracePeriodSeconds);
    
    const archivedInfo = {
      ...this.currentInfo,
      expiresAt: graceExpiry,
      isActive: false,
    };

    // 使用 Token hash 作為 key 以避免存儲原始 Token
    const tokenHash = this._hashToken(this.currentToken);
    this.previousTokens.set(tokenHash, archivedInfo);

    // 清理過期的舊 Token
    this._cleanupExpiredTokens();
  }

  /**
   * 清理過期的舊 Token
   * @private
   */
  _cleanupExpiredTokens() {
    const now = new Date();
    for (const [hash, info] of this.previousTokens.entries()) {
      if (info.expiresAt && info.expiresAt < now) {
        this.previousTokens.delete(hash);
        this._log('debug', 'token_cleanup', 'Expired token removed from grace period list');
      }
    }
  }

  /**
   * 生成新的 Token
   * @returns {{token: string, info: TokenInfo}} Token 和資訊
   */
  generateToken() {
    // 如果已有 Token，先進行歸檔處理
    if (this.currentToken !== null) {
      this._archiveCurrentToken();
    }

    // 生成新 Token
    const token = crypto.randomBytes(this.tokenLength).toString('hex');
    const tokenId = this._generateTokenId();
    const expiresAt = this._calculateExpiry();

    const info = {
      tokenId: tokenId,
      createdAt: new Date(),
      expiresAt: expiresAt,
      isActive: true,
      rotationCount: this.rotationCount,
    };

    this.currentToken = token;
    this.currentInfo = info;

    this._log('info', 'token_generated', 'Token generated', {
      tokenId: tokenId,
      expiresAt: expiresAt ? expiresAt.toISOString() : null,
    });

    return { token, info };
  }

  /**
   * 輪替 Token
   * @param {string} [reason='scheduled'] - 輪替原因
   * @returns {{token: string, info: TokenInfo}} 新 Token 和資訊
   */
  rotateToken(reason = 'scheduled') {
    const oldTokenId = this.currentInfo ? this.currentInfo.tokenId : null;

    // 增加輪替計數
    this.rotationCount++;

    // 生成新 Token（內部會歸檔舊 Token）
    const { token, info } = this.generateToken();

    // 記錄輪替事件
    const event = {
      oldTokenId: oldTokenId,
      newTokenId: info.tokenId,
      timestamp: new Date(),
      reason: reason,
    };
    this.rotationHistory.push(event);

    // 限制歷史記錄數量
    if (this.rotationHistory.length > this.maxRotationHistory) {
      this.rotationHistory = this.rotationHistory.slice(-this.maxRotationHistory);
    }

    this._log('info', 'token_rotated', 'Token rotated', {
      oldTokenId: oldTokenId,
      newTokenId: info.tokenId,
      reason: reason,
      rotationCount: this.rotationCount,
    });

    // 通知訂閱者
    for (const callback of this.rotationCallbacks) {
      try {
        callback(token, info);
      } catch (error) {
        this._log('error', 'rotation_callback_error', 'Token rotation callback error', {
          error: error.message,
        });
      }
    }

    return { token, info };
  }

  /**
   * 驗證 Token
   * @param {string} token - 要驗證的 Token
   * @returns {boolean} Token 是否有效
   */
  verifyToken(token) {
    if (!token) {
      return false;
    }

    // 檢查當前 Token
    if (this.currentToken !== null) {
      if (crypto.timingSafeEqual(Buffer.from(token), Buffer.from(this.currentToken))) {
        if (this.currentInfo && !this._isExpired(this.currentInfo)) {
          return true;
        } else {
          this._log('warn', 'token_expired', 'Current token expired');
          return false;
        }
      }
    }

    // 檢查寬限期內的舊 Token
    const tokenHash = this._hashToken(token);
    if (this.previousTokens.has(tokenHash)) {
      const info = this.previousTokens.get(tokenHash);
      if (!this._isExpired(info)) {
        this._log('debug', 'token_grace_period', 'Token verified via grace period', {
          tokenId: info.tokenId,
        });
        return true;
      }
    }

    return false;
  }

  /**
   * 取得當前 Token
   * @returns {string|null} 當前 Token
   */
  getCurrentToken() {
    return this.currentToken;
  }

  /**
   * 取得當前 Token 資訊
   * @returns {TokenInfo|null} Token 資訊
   */
  getTokenInfo() {
    if (!this.currentInfo) {
      return null;
    }

    return {
      tokenId: this.currentInfo.tokenId,
      createdAt: this.currentInfo.createdAt.toISOString(),
      expiresAt: this.currentInfo.expiresAt ? this.currentInfo.expiresAt.toISOString() : null,
      isActive: this.currentInfo.isActive,
      isExpired: this._isExpired(this.currentInfo),
      rotationCount: this.currentInfo.rotationCount,
      timeUntilExpiry: this._getTimeUntilExpiry(),
    };
  }

  /**
   * 取得距離過期的時間（秒）
   * @private
   */
  _getTimeUntilExpiry() {
    if (!this.currentInfo || !this.currentInfo.expiresAt) {
      return null;
    }
    const diff = this.currentInfo.expiresAt.getTime() - Date.now();
    return Math.max(0, Math.floor(diff / 1000));
  }

  /**
   * 取得輪替歷史
   * @returns {TokenRotationEvent[]} 輪替事件列表
   */
  getRotationHistory() {
    return this.rotationHistory.map(event => ({
      oldTokenId: event.oldTokenId,
      newTokenId: event.newTokenId,
      timestamp: event.timestamp.toISOString(),
      reason: event.reason,
    }));
  }

  /**
   * 檢查是否需要輪替
   * @param {number} [thresholdHours=1.0] - 剩餘有效時間閾值（小時）
   * @returns {boolean} 是否需要輪替
   */
  isRotationNeeded(thresholdHours = 1.0) {
    if (!this.currentInfo) {
      return true;
    }

    if (this._isExpired(this.currentInfo)) {
      return true;
    }

    const timeLeft = this._getTimeUntilExpiry();
    if (timeLeft === null) {
      return false;
    }

    return timeLeft < thresholdHours * 3600;
  }

  /**
   * 訂閱 Token 輪替事件
   * @param {Function} callback - 輪替時呼叫的回調函式 (newToken, tokenInfo) => void
   */
  onTokenRotated(callback) {
    this.rotationCallbacks.push(callback);
  }

  /**
   * 移除輪替事件訂閱
   * @param {Function} callback - 要移除的回調函式
   * @returns {boolean} 是否成功移除
   */
  removeRotationCallback(callback) {
    const index = this.rotationCallbacks.indexOf(callback);
    if (index > -1) {
      this.rotationCallbacks.splice(index, 1);
      return true;
    }
    return false;
  }

  /**
   * 使當前 Token 失效
   */
  invalidateToken() {
    this.currentToken = null;
    this.currentInfo = null;
    this.previousTokens.clear();

    this._log('warn', 'tokens_invalidated', 'All tokens invalidated');
  }

  /**
   * 取得 Token 管理器狀態
   * @returns {Object} 狀態資訊
   */
  getStatus() {
    return {
      hasToken: this.currentToken !== null,
      tokenInfo: this.getTokenInfo(),
      gracePeriodTokens: this.previousTokens.size,
      rotationCount: this.rotationCount,
      rotationHistoryCount: this.rotationHistory.length,
    };
  }
}

// 創建全域 Token 管理器實例
let globalTokenManager = null;

/**
 * 取得全域 Token 管理器
 * @param {Object} [options] - 配置選項（僅首次呼叫有效）
 * @returns {TokenManager} Token 管理器實例
 */
function getTokenManager(options = {}) {
  if (!globalTokenManager) {
    globalTokenManager = new TokenManager({
      tokenLength: 32,
      tokenExpiryHours: 24,  // 24 小時過期
      gracePeriodSeconds: 120,  // 2 分鐘寬限期
      ...options,
    });
  }
  return globalTokenManager;
}

/**
 * 重置全域 Token 管理器
 * 主要用於測試目的
 */
function resetTokenManager() {
  globalTokenManager = null;
}

module.exports = {
  TokenManager,
  getTokenManager,
  resetTokenManager,
};
