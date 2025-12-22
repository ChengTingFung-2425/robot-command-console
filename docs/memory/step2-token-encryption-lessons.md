# Step 2: Token Encryption 經驗總結

## 日期
2025-12-22

## 任務
實作 Token Encryption 模組，使用 Fernet (AES-128) 對稱加密保護 Token。

## TDD 流程執行

### 1. Red Phase ✅
撰寫 7 個測試案例（預期失敗）：
- `test_encryption_key_generation` - 加密金鑰生成
- `test_encrypt_decrypt_roundtrip` - 加密解密往返測試
- `test_encryption_produces_different_ciphertext` - 驗證 IV 隨機性
- `test_encryption_key_persistence` - 金鑰持久化
- `test_salt_uniqueness` - Salt 唯一性
- `test_decrypt_invalid_data` - 解密無效資料處理
- `test_key_file_permissions_linux` - 檔案權限驗證

### 2. Green Phase ✅
實作 `TokenEncryption` 類別：
- 使用 `cryptography.fernet.Fernet` (AES-128)
- PBKDF2 金鑰派生（100,000 iterations）
- Salt 持久化（32 bytes 隨機生成）
- 金鑰基於機器資訊（hostname + platform）
- 檔案權限 chmod 600

### 3. Refactor Phase ✅
程式碼已最佳化，無需額外重構

## 關鍵經驗

### 1. ⭐⭐⭐ Fernet 加密實作
**經驗**：
- Fernet 提供開箱即用的安全加密（AES-128 CBC + HMAC）
- 自動處理 IV/nonce 隨機性，每次加密產生不同密文
- 內建時間戳記，支援 TTL（Time-To-Live）驗證

**實作**：
```python
from cryptography.fernet import Fernet

fernet = Fernet(key)
encrypted = fernet.encrypt(data.encode('utf-8'))
decrypted = fernet.decrypt(encrypted).decode('utf-8')
```

**注意事項**：
- Fernet key 必須是 32 bytes，base64 編碼後為 44 bytes
- 加密後的資料會比原始資料大（約 57 bytes overhead）

### 2. ⭐⭐⭐ PBKDF2 金鑰派生
**經驗**：
- 使用 PBKDF2 + SHA-256 從密碼派生金鑰
- 100,000 iterations 提供足夠的抗暴力破解能力
- 結合機器資訊（hostname + platform）作為基礎密碼

**實作**：
```python
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    salt=salt,
    iterations=100000,
)
key_material = kdf.derive(base_password)
fernet_key = base64.urlsafe_b64encode(key_material)
```

**注意事項**：
- Salt 必須隨機且唯一（每個應用程式實例）
- Salt 需要持久化儲存（不能遺失）
- 金鑰派生過程耗時（約 100ms），應快取結果

### 3. ⭐⭐ Salt 管理與持久化
**經驗**：
- Salt 使用 `os.urandom(32)` 生成（加密安全的隨機數）
- 儲存至獨立檔案（`~/.robot-edge/salt`）
- 不同應用程式實例有不同 salt

**實作**：
```python
if os.path.exists(self.salt_file):
    with open(self.salt_file, 'rb') as f:
        return f.read()

salt = os.urandom(32)
with open(self.salt_file, 'wb') as f:
    f.write(salt)
```

**注意事項**：
- Salt 不是密鑰，可以公開，但應保持唯一性
- Salt 遺失會導致無法重新派生相同金鑰

### 4. ⭐⭐ 檔案權限安全
**經驗**：
- 加密金鑰檔案必須設定嚴格權限（chmod 600）
- Salt 檔案也應保護（雖然不是秘密，但避免被竄改）
- 目錄權限設為 700（僅擁有者可存取）

**實作**：
```python
os.makedirs(self.storage_dir, mode=0o700, exist_ok=True)

with open(self.key_file, 'wb') as f:
    f.write(fernet_key)

if os.name == 'posix':
    os.chmod(self.key_file, 0o600)
```

**注意事項**：
- Windows 需要使用 NTFS ACL（Step 3 實作）
- macOS 行為類似 Linux

### 5. ⭐⭐ 測試驗證 IV 隨機性
**經驗**：
- Fernet 自動為每次加密生成隨機 IV
- 相同資料多次加密應產生不同密文
- 測試應驗證此行為以確保安全性

**實作**：
```python
def test_encryption_produces_different_ciphertext(self):
    data = "same_token"
    encrypted1 = self.encryption.encrypt(data)
    encrypted2 = self.encryption.encrypt(data)
    self.assertNotEqual(encrypted1, encrypted2)
```

**注意事項**：
- 這是確保加密安全的重要測試
- 如果密文相同，可能表示 IV 未正確隨機化

### 6. ⭐ 錯誤處理
**經驗**：
- `fernet.decrypt()` 會在資料無效時拋出 `cryptography.fernet.InvalidToken`
- 測試應驗證錯誤處理行為

**實作**：
```python
def test_decrypt_invalid_data(self):
    with self.assertRaises(Exception):
        self.encryption.decrypt("invalid_encrypted_data")
```

## 測試結果

```
================================================== 7 passed in 0.44s ===================================================
```

**通過率**: 7/7 (100%)
**執行時間**: 0.44s

## 程式碼統計

- **測試檔案**: `tests/test_token_encryption.py` (~110 行)
- **實作檔案**: `src/edge_app/auth/encryption.py` (~145 行)
- **測試/實作比例**: 0.76:1

## 完成定義檢查

- [x] 7 個測試案例全部通過
- [x] 加密金鑰為 44 bytes（Fernet key）
- [x] 加密解密往返正確
- [x] 金鑰持久化
- [x] Salt 唯一性
- [x] 檔案權限 chmod 600（Linux）
- [x] 錯誤處理（無效資料）
- [x] 程式碼有完整 docstring
- [ ] Flake8 檢查（待 CI）
- [ ] CodeQL 掃描（下一步）

## 下一步

**Step 3: Platform Storage**（第 5-7 天）
- 10 個測試案例
- Linux Secret Service 整合
- Windows Credential Manager 整合
- Fallback 模式

## 參考資料

- [Cryptography Fernet Documentation](https://cryptography.io/en/latest/fernet/)
- [PBKDF2 RFC 2898](https://datatracker.ietf.org/doc/html/rfc2898)
- [NIST SP 800-132](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-132.pdf)
