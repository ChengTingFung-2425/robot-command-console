# GitHub Copilot Instructions 目錄

此目錄包含 GitHub Copilot 的指令檔案，用於定義不同檔案類型的編碼規範和指引。

## 檔案命名規範

所有指令檔案遵循以下命名格式：

```
<FileType>.instructions.md
```

例如：
- `Python.instructions.md` - Python 檔案的編碼規範
- `Markdown.instructions.md` - Markdown 檔案的編碼規範

## ⚠️ 重要：Windows 相容性

**請注意**：在引用此目錄中的檔案時，請使用以下方式：

✅ **正確方式**：
- 具體檔名：`.github/instructions/Python.instructions.md`
- 目錄引用：`.github/instructions/` 目錄
- 在程式碼中使用 glob：`.github/instructions/*.instructions.md`（僅在程式碼中）

❌ **錯誤方式**：
- 在檔名或 git 中使用字面 `*`：`.github/instructions/*.instructions.md`（作為實際檔名）
- Windows 不允許檔名包含 `*`、`?`、`<`、`>`、`|`、`"`、`:` 等字符

## 指令檔案格式

每個 `.instructions.md` 檔案包含以下部分：

### 1. Frontmatter（YAML 格式）

```yaml
---
applyTo: '**/*.py'  # glob 模式，指定適用的檔案類型
---
```

### 2. 指引內容

使用 Markdown 格式撰寫編碼規範、最佳實踐和範例。

## 目前的指令檔案

| 檔案 | 適用對象 | 說明 |
|------|---------|------|
| `Python.instructions.md` | `**/*.py` | Python 檔案格式化與開發指引 |
| `Markdown.instructions.md` | `**/*.md` | Markdown 文件撰寫規範 |

## 新增指令檔案

如需新增其他檔案類型的指引，請：

1. 建立新檔案：`<FileType>.instructions.md`
2. 加入適當的 frontmatter
3. 撰寫清晰的指引內容
4. 更新本 README

---

**最後更新**：2025-12-22
