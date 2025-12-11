# 批次檔案範例

本目錄包含各種批次操作的範例檔案，展示不同格式和使用場景。

## 檔案列表

### 1. demo_sequence.json
**格式**：JSON  
**描述**：機器人演示序列，展示基本動作組合  
**用途**：演示、展會、參觀  
**執行模式**：分組並行（grouped）

```bash
python3 run_batch_cli.py --file examples/batches/demo_sequence.json
```

### 2. test_basic.yaml
**格式**：YAML  
**描述**：自動化測試基本動作序列  
**用途**：單元測試、整合測試  
**執行模式**：順序執行（sequential）

```bash
python3 run_batch_cli.py --file examples/batches/test_basic.yaml
```

### 3. simple_batch.csv
**格式**：CSV  
**描述**：簡單的批次指令列表  
**用途**：快速原型、Excel 匯入  
**執行模式**：預設（grouped）

```bash
python3 run_batch_cli.py --file examples/batches/simple_batch.csv
```

## 使用範例

```bash
# 基本執行
python3 run_batch_cli.py --file examples/batches/demo_sequence.json

# 乾跑模式
python3 run_batch_cli.py --file examples/batches/demo_sequence.json --dry-run

# 監控模式
python3 run_batch_cli.py --file examples/batches/demo_sequence.json --monitor

# 輸出結果
python3 run_batch_cli.py --file examples/batches/demo_sequence.json --output result.json
```

## 相關文件

- [CLI 批次操作設計文件](../../docs/development/CLI_BATCH_OPERATIONS.md)
- [完整使用說明](../../docs/development/CLI_BATCH_OPERATIONS.md)
