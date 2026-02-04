# 發佈流程指南

本文件說明 Robot Command Console 的完整發佈流程。

## 發佈準備清單

### 1. 版本規劃

確定版本號（遵循語義化版本控制）：
- **Major (X.0.0)**: 重大架構變更或不相容變更
- **Minor (x.Y.0)**: 新功能或重要改進
- **Patch (x.y.Z)**: Bug 修復或小改進
- **Pre-release**: -alpha, -beta, -rc

### 2. 程式碼準備

- [ ] 所有功能開發完成
- [ ] 所有測試通過
- [ ] 程式碼審查完成
- [ ] 安全掃描通過
- [ ] 文件更新完成

### 3. 版本號更新

編輯 `src/common/version.py`：
```python
__version__ = "3.2.0"  # 移除 -beta
__version_info__ = (3, 2, 0)
RELEASE_NAME = "Phase 3.2 - Tiny Edge App"
RELEASE_DATE = "2026-02-04"
BUILD_NUMBER = "001"
```

### 4. CHANGELOG 更新

編輯 `CHANGELOG.md`：
```markdown
## [3.2.0] - 2026-02-04

### Added
- 新功能列表

### Changed
- 變更項目

### Fixed
- 修復的 bug

### Removed
- 移除的功能
```

### 5. 文件更新

- [ ] 更新 README.md（版本號、功能列表）
- [ ] 更新 docs/proposal.md（如有架構變更）
- [ ] 更新用戶指南
- [ ] 檢查所有連結有效性

## 發佈流程

### 方式一：自動發佈（推薦）

#### 1. 建立並推送標籤

```bash
# 確保在 main 分支
git checkout main
git pull origin main

# 建立標籤
git tag -a v3.2.0 -m "Release v3.2.0 - Tiny Edge App"

# 推送標籤（觸發 GitHub Actions）
git push origin v3.2.0
```

#### 2. 等待 GitHub Actions 完成

工作流程 `release.yml` 會自動：
1. 建立 GitHub Release
2. 構建所有平台的打包檔案
3. 上傳打包檔案到 Release
4. 生成 Release Notes

監控進度：
```
https://github.com/ChengTingFung-2425/robot-command-console/actions
```

#### 3. 驗證 Release

檢查 Release 頁面：
```
https://github.com/ChengTingFung-2425/robot-command-console/releases
```

確認：
- [ ] Release Notes 完整
- [ ] 所有平台的打包檔案已上傳
- [ ] 下載連結可用
- [ ] Pre-release 標記正確（如適用）

### 方式二：手動發佈

#### 1. 本地構建

```bash
# 啟動虛擬環境
source .venv/bin/activate

# 建立啟動畫面
python Edge/qtwebview-app/resources/images/create_splash_image.py

# 執行打包
pyinstaller Edge/qtwebview-app/build.spec

# 建立壓縮檔
cd dist
tar -czf RobotConsole-$(uname -s).tar.gz RobotConsole/
```

#### 2. 手動建立 Release

1. 前往 GitHub Releases 頁面
2. 點擊 "Draft a new release"
3. 填寫：
   - Tag: v3.2.0
   - Title: Release v3.2.0
   - Description: 從 CHANGELOG 複製內容
4. 上傳構建產物
5. 發佈

## 發佈後工作

### 1. 驗證下載

測試各平台下載連結：
```bash
# Linux
wget https://github.com/.../RobotConsole-linux.tar.gz
tar -xzf RobotConsole-linux.tar.gz
./RobotConsole/RobotConsole

# Windows (PowerShell)
Invoke-WebRequest -Uri https://github.com/.../RobotConsole-windows.zip -OutFile RobotConsole.zip
Expand-Archive RobotConsole.zip
.\RobotConsole\RobotConsole.exe

# macOS
curl -L https://github.com/.../RobotConsole-macos.tar.gz -o RobotConsole.tar.gz
tar -xzf RobotConsole.tar.gz
open RobotConsole.app
```

### 2. 更新文件網站

如有文件網站，更新：
- 版本號
- 下載連結
- 發佈公告

### 3. 通知用戶

- [ ] 發佈 Release 公告（GitHub Discussions）
- [ ] 更新專案首頁
- [ ] 社群媒體公告（如適用）
- [ ] 電子郵件通知（如有訂閱列表）

### 4. 準備下一版本

```bash
# 建立開發分支
git checkout -b develop

# 更新版本號為下一版本
vim src/common/version.py
# __version__ = "3.3.0-alpha"

# 提交
git commit -am "Prepare for v3.3.0 development"
git push origin develop
```

## Pre-release 發佈

### Alpha 版本

```bash
git tag -a v3.3.0-alpha.1 -m "Alpha release for testing"
git push origin v3.3.0-alpha.1
```

特點：
- 主要用於內部測試
- 可能有未完成功能
- 可能不穩定

### Beta 版本

```bash
git tag -a v3.3.0-beta.1 -m "Beta release for public testing"
git push origin v3.3.0-beta.1
```

特點：
- 功能完整
- 需要廣泛測試
- 可能有小 bug

### Release Candidate

```bash
git tag -a v3.3.0-rc.1 -m "Release candidate"
git push origin v3.3.0-rc.1
```

特點：
- 準備正式發佈
- 僅修復關鍵 bug
- 不添加新功能

## 緊急修復（Hotfix）

### 流程

```bash
# 1. 基於 release 標籤建立 hotfix 分支
git checkout -b hotfix/v3.2.1 v3.2.0

# 2. 修復 bug
vim src/...
git commit -am "Fix critical bug"

# 3. 更新版本號
vim src/common/version.py  # 3.2.1
vim CHANGELOG.md

# 4. 建立標籤
git tag -a v3.2.1 -m "Hotfix: Critical bug fix"

# 5. 合併回 main
git checkout main
git merge --no-ff hotfix/v3.2.1
git push origin main

# 6. 推送標籤觸發發佈
git push origin v3.2.1

# 7. 合併回 develop
git checkout develop
git merge --no-ff hotfix/v3.2.1
git push origin develop
```

## 回滾發佈

如發現嚴重問題需要回滾：

### 1. 標記為 Pre-release

在 GitHub Release 頁面：
1. 編輯 Release
2. 勾選 "This is a pre-release"
3. 添加警告訊息

### 2. 發佈修復版本

```bash
# 遵循 Hotfix 流程發佈修復版本
git tag -a v3.2.1 -m "Fix issues in v3.2.0"
git push origin v3.2.1
```

### 3. 通知用戶

- 在原 Release 添加警告
- 發佈公告說明問題
- 指引用戶升級到修復版本

## 自動化腳本

### release.sh

```bash
#!/bin/bash
# 自動化發佈腳本

VERSION=$1

if [ -z "$VERSION" ]; then
    echo "Usage: ./release.sh <version>"
    echo "Example: ./release.sh 3.2.0"
    exit 1
fi

echo "Preparing release v$VERSION..."

# 更新版本號
sed -i "s/__version__ = \".*\"/__version__ = \"$VERSION\"/" src/common/version.py

# 更新 CHANGELOG
DATE=$(date +%Y-%m-%d)
sed -i "s/## \[Unreleased\]/## [$VERSION] - $DATE/" CHANGELOG.md

# 提交變更
git add src/common/version.py CHANGELOG.md
git commit -m "Bump version to $VERSION"

# 建立標籤
git tag -a "v$VERSION" -m "Release v$VERSION"

# 推送
git push origin main
git push origin "v$VERSION"

echo "✓ Release v$VERSION created!"
echo "Monitor: https://github.com/ChengTingFung-2425/robot-command-console/actions"
```

## 檢查清單

### 發佈前

- [ ] 所有測試通過
- [ ] 安全掃描通過
- [ ] 程式碼審查完成
- [ ] 版本號已更新
- [ ] CHANGELOG 已更新
- [ ] 文件已更新
- [ ] 標籤已建立並推送

### 發佈後

- [ ] Release 已建立
- [ ] 打包檔案已上傳
- [ ] 下載連結可用
- [ ] Release Notes 完整
- [ ] 用戶已通知
- [ ] 問題追蹤已更新

## 問題回報

發佈遇到問題時：
1. 檢查 GitHub Actions 日誌
2. 查看 BUILD.md 疑難排解章節
3. 回報到 Issues 並標記 `release`

---

**最後更新**: 2026-02-04  
**維護者**: DevOps Team  
**相關文件**: [BUILD.md](BUILD.md), [CHANGELOG.md](CHANGELOG.md)
