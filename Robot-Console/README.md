# Robot-Console 模組

機器人指令抽象層 - 根據 module.md 設計文件完整重建

## 📚 文件

- [module.md](module.md) - 完整模組設計說明
- [契約定義](../docs/contract/) - JSON Schema 契約檔案

## 🎯 核心功能

- ✅ 統一的機器人指令抽象介面
- ✅ 支援 38+ 預定義動作（移動、控制、手勢、運動、格鬥、舞蹈）
- ✅ 非同步執行引擎（優先權佇列、超時控制）
- ✅ 緊急停止機制（最高優先權）
- ✅ 多協定支援（MQTT/HTTP/WebSocket）
- ✅ 標準化契約（完全對齊 MCP）
- ✅ 端到端追蹤（trace_id）

## 🚀 快速開始

```bash
# 安裝依賴
./create_virtual_env.sh

# 查看模組說明
cat module.md

# 查看設定範例
cat settings.yaml
```

## 📖 詳細說明

請參閱 [module.md](module.md) 以獲取：
- 模組定位與架構
- 標準化契約格式
- 所有支援的動作清單
- 擴充指南
- 安全性設計

## 📝 授權

MIT License
