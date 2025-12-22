# Step 1: Device ID Generator - 經驗總結

## 實作日期
2025-12-22

## 實作內容
Phase 2.1 Step 1: Device ID Generator（TDD 流程）

## TDD 流程執行結果

### ✅ Red Phase（測試先行）
- 建立 `tests/test_device_id_generator.py`
- 撰寫 8 個測試案例
- 預期結果：所有測試跳過/失敗 ✅

### ✅ Green Phase（實作功能）
- 建立 `src/edge_app/auth/device_id.py`
- 實作 `DeviceIDGenerator` 類別
- 預期結果：所有測試通過 ✅

### ✅ Refactor Phase（重構）
- 程式碼已最佳化
- 無需額外重構

## 測試結果

```
Ran 8 tests in 0.007s
OK
```

**通過率**: 8/8 (100%)

## 測試案例清單

1. ✅ `test_generate_returns_string` - Device ID 回傳字串
2. ✅ `test_generate_returns_64_char_hex` - Device ID 為 64 字元 SHA-256
3. ✅ `test_generate_is_stable` - Device ID 穩定性
4. ✅ `test_get_or_create_creates_new_id` - 建立新 ID
5. ✅ `test_get_or_create_persists_to_file` - ID 持久化
6. ✅ `test_get_or_create_returns_cached_id` - 讀取快取 ID
7. ✅ `test_device_id_file_permissions` - 檔案權限 (chmod 600)
8. ✅ `test_handles_corrupted_device_id_file` - 處理損壞檔案

## 關鍵經驗

### 1. TDD 流程嚴格執行 ⭐⭐⭐
**經驗**：嚴格按照 Red-Green-Refactor 循環執行，確保測試先行。

**原因**：
- 測試先行迫使思考 API 設計
- 確保每個功能都有測試覆蓋
- 避免過度設計（YAGNI 原則）

**範例**：
```python
# 1. 先寫測試（Red）
def test_generate_returns_64_char_hex(self):
    device_id = DeviceIDGenerator.generate()
    self.assertEqual(len(device_id), 64)

# 2. 實作功能（Green）
def generate() -> str:
    combined = "|".join(characteristics)
    return hashlib.sha256(combined.encode('utf-8')).hexdigest()
```

### 2. Device ID 穩定性設計 ⭐⭐⭐
**經驗**：使用多個機器特徵組合生成 Device ID，確保穩定性。

**實作**：
```python
characteristics = [
    mac_address,      # 最穩定
    hostname,         # 次穩定
    platform_info,    # 輔助
    cpu_info          # 選用
]
```

**注意事項**：
- MAC address 優先（最穩定）
- 加入多個 fallback 避免無法生成
- 使用 SHA-256 確保唯一性

### 3. 檔案權限安全 ⭐⭐
**經驗**：Linux 環境下設定 chmod 600 限制檔案訪問。

**實作**：
```python
if os.name != 'nt':  # Not Windows
    os.chmod(storage_path, 0o600)
```

**平台差異**：
- Linux: chmod 600（僅擁有者可讀寫）
- Windows: NTFS ACL（需額外處理，Step 3 實作）

### 4. 錯誤處理與容錯 ⭐⭐
**經驗**：處理損壞的 Device ID 檔案，自動重新生成。

**實作**：
```python
try:
    device_id = f.read().strip()
    if len(device_id) == 64:
        int(device_id, 16)  # 驗證 hex
        return device_id
except Exception:
    pass  # 重新生成
```

### 5. Import 路徑問題 ⭐
**問題**：測試檔案 import 失敗。

**解決方案**：
```python
# 錯誤: ../..' (多了一層)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# 正確: ..' (正確路徑)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
```

## 完成定義檢查

- [x] 8 個測試案例全部通過
- [x] Device ID 為 64 字元 SHA-256
- [x] Device ID 穩定（同機器同 ID）
- [x] 檔案持久化
- [x] 檔案權限 chmod 600（Linux）
- [x] 處理損壞檔案
- [x] 程式碼有完整 docstring
- [ ] Flake8 檢查（工具未安裝，待 CI 檢查）
- [ ] CodeQL 掃描（下一步）

## 下一步

**Step 2: Token Encryption**
- 預計時間：第 3-4 天
- 測試案例：6 個
- 功能：Fernet 加密、金鑰派生

## 檔案清單

**新增檔案**：
1. `src/edge_app/__init__.py`
2. `src/edge_app/auth/__init__.py`（更新）
3. `src/edge_app/auth/device_id.py`
4. `tests/test_device_id_generator.py`

**程式碼統計**：
- 實作程式碼：~130 行
- 測試程式碼：~130 行
- 測試/實作比例：1:1
