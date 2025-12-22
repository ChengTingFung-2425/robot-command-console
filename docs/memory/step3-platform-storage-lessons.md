# Step 3: Platform Storage - 經驗總結

## 基本資訊

**日期**: 2025-12-22  
**步驟**: Phase 2.1 Step 3  
**模組**: Platform Storage  
**測試**: 10/10 通過 (100%)  
**累計測試**: 25/51 通過 (49%)

## 實作摘要

實作 PlatformStorage 類別，提供跨平台的安全 Token 儲存功能，支援 Linux Secret Service API、Windows Credential Manager 與 Fallback 加密檔案儲存。

### 核心功能

1. **平台自動偵測**
   - Linux: `platform.system() == 'Linux'`
   - Windows: `platform.system() == 'Windows'`
   - 自動選擇最佳儲存方式

2. **Linux Secret Service API**
   - 使用 `secretstorage` 模組
   - D-Bus 通訊
   - GNOME Keyring/KWallet 整合

3. **Windows Credential Manager**
   - 使用 `keyring` 模組
   - Windows API 整合
   - 系統原生安全儲存

4. **Fallback 加密檔案**
   - Fernet 對稱加密
   - 應用程式隔離（檔名含 app_name）
   - 檔案權限控管（chmod 600）

## 關鍵經驗

### 1. **平台特定模組的 Mock 測試** ⭐⭐⭐

**問題**: `secretstorage` 和 `keyring` 在 CI 環境中不可用

**解決方案**: 使用 `patch.dict('sys.modules', {...})` mock 整個模組

```python
with patch.dict('sys.modules', {'secretstorage': mock_secretstorage}):
    storage = PlatformStorage(self.app_name)
    # 測試程式碼
```

**重要性**: ⭐⭐⭐  
**適用場景**: 測試平台特定功能時，避免依賴環境安裝

### 2. **Fallback 模式設計** ⭐⭐⭐

**設計原則**:
- 主動偵測平台原生儲存可用性
- 失敗時自動 fallback 至檔案儲存
- Fallback 模式同樣安全（加密）

**實作要點**:
```python
def _init_native_storage(self):
    try:
        import secretstorage
        self._use_native = True
    except Exception:
        pass  # Use fallback
```

**重要性**: ⭐⭐⭐  
**適用場景**: 跨平台應用、環境不確定時

### 3. **應用程式隔離機制** ⭐⭐

**實作**: 檔名包含 app_name
- `secrets_{app_name}.enc`
- `storage_key_{app_name}.key`

**好處**:
- 多應用程式可共存
- 避免資料混淆
- 提高安全性

**重要性**: ⭐⭐  
**適用場景**: 多租戶系統、共用環境

### 4. **加密金鑰管理** ⭐⭐⭐

**設計**:
- 每個應用程式獨立金鑰
- 金鑰持久化（避免重新加密）
- 金鑰檔案權限 chmod 600

**實作**:
```python
def _get_encryption_key(self) -> bytes:
    key_file = self.storage_dir / f"storage_key_{self.app_name}.key"
    if key_file.exists():
        return key_file.read_bytes()
    key = Fernet.generate_key()
    key_file.write_bytes(key)
    os.chmod(key_file, 0o600)
    return key
```

**重要性**: ⭐⭐⭐  
**適用場景**: 加密資料持久化

### 5. **錯誤處理與容錯** ⭐⭐

**策略**:
- 所有平台特定操作都有 try-except
- 失敗不拋出異常，返回 False
- 自動 fallback 機制

**範例**:
```python
def _save_linux(self, key: str, value: str) -> bool:
    try:
        # Linux Secret Service 操作
        return True
    except Exception:
        return False  # Trigger fallback
```

**重要性**: ⭐⭐  
**適用場景**: 跨平台應用、生產環境

### 6. **D-Bus 與 Secret Service** ⭐⭐

**Linux 原生儲存**:
- D-Bus 通訊協定
- Secret Service API 規範
- 支援 GNOME Keyring 與 KWallet

**重要概念**:
- Connection: D-Bus 連線
- Collection: Secret 集合（如 keyring）
- Item: 單一 secret

**重要性**: ⭐⭐  
**適用場景**: Linux 桌面應用

## 測試統計

| 測試項目 | 數量 | 狀態 |
|---------|------|------|
| 平台偵測 | 2 | ✅ 通過 |
| Linux Secret Service | 3 | ✅ 通過 |
| Windows Credential Manager | 2 | ✅ 通過 |
| Fallback 模式 | 1 | ✅ 通過 |
| 加密驗證 | 1 | ✅ 通過 |
| 應用程式隔離 | 1 | ✅ 通過 |
| **總計** | **10** | **✅ 100%** |

## 程式碼統計

- **實作檔案**: `src/edge_app/auth/platform_storage.py`
- **測試檔案**: `tests/test_platform_storage.py`
- **實作行數**: ~280 行
- **測試行數**: ~175 行
- **測試/實作比例**: 0.63:1
- **測試執行時間**: 0.180s（10 測試）

## 完成定義檢查

- [x] 10 個測試案例全部通過
- [x] Linux 平台偵測正確
- [x] Windows 平台偵測正確
- [x] Linux Secret Service Mock 測試
- [x] Windows Credential Manager Mock 測試
- [x] Fallback 模式運作正常
- [x] 檔案加密儲存（非明文）
- [x] 應用程式隔離
- [x] 程式碼有完整 docstring
- [ ] Flake8 檢查（待 CI）
- [ ] CodeQL 掃描（下一步）

## 下一步

**Step 4: Edge Token Cache（第 8-10 天）**
- 15 個測試案例
- 整合 DeviceIDGenerator、TokenEncryption、PlatformStorage
- Token 過期邏輯
- 使用者資訊管理

---

**狀態**: ✅ Step 3 完成  
**累計進度**: 25/51 測試（49%）  
**預計時程**: 7 天剩餘（Step 4-6）
