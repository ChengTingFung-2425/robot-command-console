# Phase 2.1: Edge Token Cache 實作計劃

## 專案資訊

**版本**: v1.0  
**建立日期**: 2025-12-22  
**負責人**: Edge App Team  
**預計時程**: 2 週  
**優先級**: 高  

## 目標

實作 Edge Token Cache 模組，提供安全的 Token 儲存與管理功能，支援 Linux（優先）與 Windows（次要）平台。

## 前置條件

- ✅ Phase 1: Server 端認證 API 已完成
- ✅ 威脅模型 v2.0 已更新
- ✅ Edge App Native Desktop Integration 設計已完成
- ✅ 平台優先順序已確認：Linux > Windows > macOS（不發布）

## 架構設計

### 模組結構

```
src/edge_app/auth/
├── __init__.py           # 模組初始化
├── token_cache.py        # 主要實作
├── device_id.py          # Device ID 生成器
├── encryption.py         # 加密工具
└── platform_storage.py   # 平台專用儲存
```

### 核心類別

#### EdgeTokenCache

```python
class EdgeTokenCache:
    """Edge Token 快取管理器
    
    功能：
    - Token 加密儲存
    - 自動過期檢測
    - Device ID 管理
    - 平台自適應儲存
    """
    
    def __init__(self, app_name: str = "robot-edge")
    def save_tokens(self, access_token: str, refresh_token: str, 
                   device_id: str, user_info: Dict) -> bool
    def get_access_token(self) -> Optional[str]
    def get_refresh_token(self) -> Optional[str]
    def is_access_token_valid(self) -> bool
    def is_refresh_token_valid(self) -> bool
    def clear_tokens(self) -> bool
    def get_device_id(self) -> str
    def get_user_info(self) -> Optional[Dict]
```

#### DeviceIDGenerator

```python
class DeviceIDGenerator:
    """Device ID 生成器
    
    功能：
    - 生成穩定的 Device ID
    - 使用機器特徵（MAC + hostname + CPU + platform）
    - SHA-256 hash
    - 持久化儲存
    """
    
    @staticmethod
    def generate() -> str
    
    @staticmethod
    def get_or_create() -> str
```

#### TokenEncryption

```python
class TokenEncryption:
    """Token 加密工具
    
    功能：
    - Fernet 對稱加密
    - 金鑰派生（PBKDF2）
    - Salt 管理
    """
    
    def __init__(self)
    def encrypt(self, data: str) -> bytes
    def decrypt(self, encrypted_data: bytes) -> str
    def get_encryption_key(self) -> bytes
```

#### PlatformStorage

```python
class PlatformStorage:
    """平台專用儲存
    
    支援：
    - Linux: Secret Service API (優先)
    - Windows: Credential Manager (次要)
    - Fallback: 加密檔案
    """
    
    def __init__(self, app_name: str)
    def save_secret(self, key: str, value: str) -> bool
    def get_secret(self, key: str) -> Optional[str]
    def delete_secret(self, key: str) -> bool
    def is_available(self) -> bool
```

### 資料結構

#### Token 資料

```python
{
    "access_token": str,        # JWT Access Token
    "access_exp": int,          # Unix timestamp
    "refresh_token": str,       # JWT Refresh Token  
    "refresh_exp": int,         # Unix timestamp
    "device_id": str,           # Device ID (64 chars)
    "user_info": {              # 使用者資訊
        "id": int,
        "username": str,
        "role": str
    },
    "created_at": int,          # Unix timestamp
    "updated_at": int           # Unix timestamp
}
```

## TDD 實作步驟

### Step 1: Device ID Generator（第 1-2 天）

#### 1.1 建立測試檔案

**檔案**: `tests/test_device_id_generator.py`

**測試案例**（8 個）:
- ✅ `test_generate_device_id_format` - Device ID 格式正確（64 字元 hex）
- ✅ `test_device_id_stability` - 同一台機器多次生成相同 ID
- ✅ `test_device_id_uniqueness` - 不同機器生成不同 ID（Mock）
- ✅ `test_get_or_create_first_time` - 首次建立 Device ID
- ✅ `test_get_or_create_existing` - 讀取已存在的 Device ID
- ✅ `test_device_id_persistence` - Device ID 持久化儲存
- ✅ `test_device_id_file_permissions_linux` - Linux 檔案權限 chmod 600
- ✅ `test_device_id_corrupted_file` - 損壞檔案處理

**執行**:
```bash
python -m pytest tests/test_device_id_generator.py -v
```

**預期**: 8 failed（測試先寫，實作後通過）

#### 1.2 實作 Device ID Generator

**檔案**: `src/edge_app/auth/device_id.py`

**實作要點**:
- 使用 `psutil` 取得系統資訊
- 使用 `hashlib.sha256()` 生成 hash
- 儲存至 `~/.robot-edge/device_id`（Linux）或 `%APPDATA%\robot-edge\device_id`（Windows）
- Linux 檔案權限：`os.chmod(file_path, 0o600)`

**驗證**:
```bash
python -m pytest tests/test_device_id_generator.py -v
# 預期: 8 passed
```

### Step 2: Token Encryption（第 3-4 天）

#### 2.1 建立測試檔案

**檔案**: `tests/test_token_encryption.py`

**測試案例**（6 個）:
- ✅ `test_encryption_key_generation` - 加密金鑰生成
- ✅ `test_encrypt_decrypt_roundtrip` - 加密解密往返測試
- ✅ `test_encryption_key_persistence` - 金鑰持久化
- ✅ `test_salt_uniqueness` - Salt 唯一性
- ✅ `test_decrypt_invalid_data` - 解密無效資料
- ✅ `test_key_derivation_with_machine_info` - 金鑰派生使用機器資訊

**執行**:
```bash
python -m pytest tests/test_token_encryption.py -v
```

**預期**: 6 failed

#### 2.2 實作 Token Encryption

**檔案**: `src/edge_app/auth/encryption.py`

**實作要點**:
- 使用 `cryptography.fernet.Fernet`
- PBKDF2 金鑰派生：`PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000)`
- Salt 儲存至 `~/.robot-edge/salt`
- 金鑰結合機器特徵（Device ID）

**驗證**:
```bash
python -m pytest tests/test_token_encryption.py -v
# 預期: 6 passed
```

### Step 3: Platform Storage（第 5-7 天）

#### 3.1 建立測試檔案

**檔案**: `tests/test_platform_storage.py`

**測試案例**（10 個）:
- ✅ `test_linux_platform_detection` - Linux 平台偵測
- ✅ `test_windows_platform_detection` - Windows 平台偵測
- ✅ `test_linux_secret_service_available` - Linux Secret Service 可用性（Mock）
- ✅ `test_linux_secret_service_save` - Linux 儲存 secret（Mock）
- ✅ `test_linux_secret_service_get` - Linux 讀取 secret（Mock）
- ✅ `test_windows_credential_manager_save` - Windows 儲存（Mock）
- ✅ `test_windows_credential_manager_get` - Windows 讀取（Mock）
- ✅ `test_fallback_to_file_storage` - Fallback 模式
- ✅ `test_file_storage_encryption` - 檔案加密儲存
- ✅ `test_storage_isolation` - 多應用程式隔離

**執行**:
```bash
python -m pytest tests/test_platform_storage.py -v
```

**預期**: 10 failed

#### 3.2 實作 Platform Storage

**檔案**: `src/edge_app/auth/platform_storage.py`

**實作要點**:
- Linux: `secretstorage` + D-Bus
- Windows: `keyring` 或 `pywin32`
- Fallback: 加密檔案 `~/.robot-edge/secrets.enc`
- 自動偵測平台與可用性
- 錯誤處理與 fallback

**驗證**:
```bash
python -m pytest tests/test_platform_storage.py -v
# 預期: 10 passed
```

### Step 4: Edge Token Cache（第 8-10 天）

#### 4.1 建立測試檔案

**檔案**: `tests/test_edge_token_cache.py`

**測試案例**（15 個）:
- ✅ `test_save_tokens` - 儲存 Token
- ✅ `test_get_access_token` - 讀取 Access Token
- ✅ `test_get_refresh_token` - 讀取 Refresh Token
- ✅ `test_access_token_expiration_check` - Access Token 過期檢測
- ✅ `test_refresh_token_expiration_check` - Refresh Token 過期檢測
- ✅ `test_get_device_id` - 取得 Device ID
- ✅ `test_get_user_info` - 取得使用者資訊
- ✅ `test_clear_tokens` - 清除 Token
- ✅ `test_no_tokens_initially` - 初始無 Token
- ✅ `test_token_overwrite` - Token 覆寫
- ✅ `test_corrupted_token_file` - 損壞檔案處理
- ✅ `test_invalid_json_in_token_file` - 無效 JSON 處理
- ✅ `test_token_cache_with_platform_storage` - 平台儲存整合
- ✅ `test_token_cache_fallback_mode` - Fallback 模式
- ✅ `test_concurrent_access_safety` - 並發存取安全性（選用）

**執行**:
```bash
python -m pytest tests/test_edge_token_cache.py -v
```

**預期**: 15 failed

#### 4.2 實作 Edge Token Cache

**檔案**: `src/edge_app/auth/token_cache.py`

**實作要點**:
- 整合 DeviceIDGenerator
- 整合 TokenEncryption
- 整合 PlatformStorage
- Token 過期邏輯：比較 `exp` 與 `time.time()`
- 錯誤處理與日誌

**驗證**:
```bash
python -m pytest tests/test_edge_token_cache.py -v
# 預期: 15 passed
```

#### 4.3 建立模組初始化

**檔案**: `src/edge_app/auth/__init__.py`

```python
"""Edge App 認證模組

提供：
- EdgeTokenCache: Token 快取管理
- DeviceIDGenerator: Device ID 生成
- TokenEncryption: Token 加密
- PlatformStorage: 平台儲存
"""

from .token_cache import EdgeTokenCache
from .device_id import DeviceIDGenerator
from .encryption import TokenEncryption
from .platform_storage import PlatformStorage

__all__ = [
    'EdgeTokenCache',
    'DeviceIDGenerator',
    'TokenEncryption',
    'PlatformStorage',
]
```

### Step 5: 整合測試（第 11-12 天）

#### 5.1 建立整合測試

**檔案**: `tests/test_edge_token_cache_integration.py`

**測試案例**（5 個）:
- ✅ `test_full_token_lifecycle` - 完整生命週期（儲存→讀取→過期→清除）
- ✅ `test_token_refresh_workflow` - Token 更新流程
- ✅ `test_device_binding` - Device ID 綁定驗證
- ✅ `test_platform_specific_storage` - 平台專用儲存（需要實際環境）
- ✅ `test_error_recovery` - 錯誤恢復機制

**執行**:
```bash
python -m pytest tests/test_edge_token_cache_integration.py -v
```

#### 5.2 效能測試

**檔案**: `tests/test_edge_token_cache_performance.py`

**測試案例**（3 個）:
- ✅ `test_token_read_performance` - 讀取效能（<5ms）
- ✅ `test_token_write_performance` - 寫入效能（<10ms）
- ✅ `test_memory_usage` - 記憶體占用（<10MB）

#### 5.3 安全測試

**檔案**: `tests/test_edge_token_cache_security.py`

**測試案例**（4 個）:
- ✅ `test_file_permissions` - 檔案權限檢查
- ✅ `test_encryption_strength` - 加密強度驗證
- ✅ `test_no_plaintext_tokens` - 無明文 Token
- ✅ `test_device_id_binding_enforcement` - Device ID 綁定強制執行

### Step 6: 文件與 Lint（第 13-14 天）

#### 6.1 程式碼文件

- Docstring（Google Style）
- 類型提示（Type Hints）
- 使用範例

#### 6.2 Lint 檢查

```bash
# Flake8
flake8 src/edge_app/auth/ --max-line-length=120 --select=E,F,W

# Mypy（類型檢查）
mypy src/edge_app/auth/ --strict

# Black（格式化）
black src/edge_app/auth/
```

#### 6.3 更新文件

- 更新 `docs/security/approach-b-implementation.md`（Phase 2.1 完成）
- 更新 `README.md`（安裝與使用）
- 新增 API 文件

## 測試統計目標

| 模組 | 測試案例數 | 覆蓋率目標 |
|------|----------|-----------|
| device_id.py | 8 | >95% |
| encryption.py | 6 | >95% |
| platform_storage.py | 10 | >90% |
| token_cache.py | 15 | >95% |
| 整合測試 | 5 | - |
| 效能測試 | 3 | - |
| 安全測試 | 4 | - |
| **總計** | **51** | **>90%** |

## 依賴管理

### 必要依賴

**Linux**:
```txt
cryptography>=41.0.0
psutil>=5.9.0
secretstorage>=3.3.0
dbus-python>=1.2.0  # Linux only
```

**Windows**:
```txt
cryptography>=41.0.0
psutil>=5.9.0
keyring>=24.0.0
pywin32>=305  # Windows only
```

### 開發依賴

```txt
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-mock>=3.11.0
pytest-timeout>=2.1.0
black>=23.0.0
flake8>=6.0.0
mypy>=1.5.0
```

## 風險與緩解

### 風險 1：平台 API 不可用

**風險**: Secret Service API 或 Credential Manager 不可用

**緩解**:
- 實作 Fallback 模式（加密檔案）
- 在初始化時檢測可用性
- 提供明確錯誤訊息

### 風險 2：加密金鑰洩漏

**風險**: 加密金鑰被不當儲存或傳輸

**緩解**:
- 金鑰派生使用機器特徵
- 不在程式碼中硬編碼
- 檔案權限嚴格限制（chmod 600）

### 風險 3：Token 過期處理

**風險**: Token 過期後無法自動更新

**緩解**:
- 在 Phase 2.2 實作自動更新機制
- 過期 Token 返回 None
- 提供明確的過期狀態

### 風險 4：跨平台相容性

**風險**: 不同平台行為不一致

**緩解**:
- 每個平台獨立測試
- 使用平台專用 Mock
- CI/CD 多平台測試

## 驗收標準

### 功能驗收

- ✅ 所有 51 個測試通過
- ✅ 程式碼覆蓋率 >90%
- ✅ Linux 與 Windows 平台驗證通過
- ✅ Token 儲存與讀取正常
- ✅ 過期檢測正確
- ✅ Device ID 穩定且唯一

### 效能驗收

- ✅ Token 讀取 <5ms
- ✅ Token 寫入 <10ms
- ✅ 記憶體占用 <10MB

### 安全驗收

- ✅ Token 加密儲存
- ✅ 檔案權限正確（chmod 600）
- ✅ 無明文 Token
- ✅ Device ID 綁定強制執行

### 品質驗收

- ✅ Flake8 無 E/F/W 級別問題
- ✅ Mypy 類型檢查通過
- ✅ Black 格式化通過
- ✅ 文件完整（Docstring + API doc）

## 下一階段

Phase 2.1 完成後，進入 **Phase 2.2: GUI 模式整合**：
- PyQt6 登入視窗
- Token 自動載入與更新
- 過期提示 UI
- 離線模式指示器

---

**文件版本**: v1.0  
**最後更新**: 2025-12-22  
**狀態**: 待實作
