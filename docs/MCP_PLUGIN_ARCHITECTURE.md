
# MCP 插件架構指南

本文件說明 MCP (Model Context Protocol) 服務的插件架構，包括如何開發和整合新的指令插件與裝置驅動插件。

## 概覽

MCP 插件架構提供模組化、可擴充的方式來：
- 擴充進階指令處理能力
- 整合機器人物理模組（攝影機、感測器等）
- 整合外部服務（WebUI、第三方 API 等）

## 插件類型

### 1. 指令插件 (CommandPlugin)
處理複雜的機器人指令序列，如巡邏、跳舞、展示等。

**特點**：
- 將高階指令展開為基本動作序列
- 支援參數驗證與 schema 定義
- 可組合多個基本動作

**範例**：
- `AdvancedCommandPlugin`: 處理巡邏、跳舞、打招呼等複雜指令
- `WebUICommandPlugin`: 處理 WebUI 特定指令（緊急停止、視訊控制等）

### 2. 裝置插件 (DevicePlugin)
整合機器人物理模組，提供標準化的裝置存取介面。

**特點**：
- 統一的資料讀寫介面
- 支援串流模式
- 裝置健康監控

**範例**：
- `CameraPlugin`: 攝影機模組（拍照、視訊串流）
- `SensorPlugin`: 感測器模組（超音波、IMU、溫度、電池）

### 3. 整合插件 (IntegrationPlugin)
整合外部服務或系統。

**特點**：
- 橋接外部 API
- 資料格式轉換
- 事件轉發

## 開發指令插件

### 1. 建立插件類別

```python
from MCP.plugin_base import (
    CommandPluginBase,
    PluginCapability,
    PluginConfig,
    PluginMetadata,
    PluginType,
)

class MyCommandPlugin(CommandPluginBase):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="my_command",
            version="1.0.0",
            author="Your Name",
            description="處理自訂指令",
            plugin_type=PluginType.COMMAND,
            capabilities=PluginCapability(
                supports_streaming=False,
                supports_async=True,
                supports_batch=True
            )
        )
    
    async def _on_initialize(self) -> bool:
        """初始化插件"""
        self.logger.info("初始化自訂指令插件")
        return True
    
    async def _on_shutdown(self) -> bool:
        """關閉插件"""
        self.logger.info("關閉自訂指令插件")
        return True
    
    def get_supported_commands(self) -> List[str]:
        """返回支援的指令列表"""
        return ["custom_action", "special_move"]
    
    def get_command_schema(self, command_name: str) -> Optional[Dict[str, Any]]:
        """返回指令參數 schema"""
        if command_name == "custom_action":
            return {
                "type": "object",
                "properties": {
                    "speed": {
                        "type": "string",
                        "enum": ["slow", "normal", "fast"]
                    },
                    "duration_ms": {
                        "type": "integer",
                        "minimum": 1000,
                        "maximum": 10000
                    }
                },
                "required": ["speed"]
            }
        return None
    
    async def execute_command(
        self,
        command_name: str,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """執行指令"""
        if command_name == "custom_action":
            return await self._execute_custom_action(parameters)
        
        return {
            "success": False,
            "error": f"不支援的指令: {command_name}"
        }
    
    async def _execute_custom_action(
        self,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """執行自訂動作"""
        speed = parameters.get("speed", "normal")
        duration_ms = parameters.get("duration_ms", 3000)
        
        # 將高階指令展開為基本動作
        actions = [
            {"action_name": "go_forward", "duration_ms": duration_ms},
            {"action_name": "turn_left", "duration_ms": 1000}
        ]
        
        return {
            "success": True,
            "command": "custom_action",
            "actions": actions,
            "message": f"自訂動作已展開為 {len(actions)} 個基本動作"
        }
```

### 2. 註冊插件

```python
from MCP.plugin_manager import PluginManager
from MCP.plugin_base import PluginConfig

plugin_manager = PluginManager()

# 註冊插件
plugin_manager.register_plugin(
    MyCommandPlugin,
    PluginConfig(enabled=True, priority=50)
)

# 初始化
await plugin_manager.initialize_all()
```

### 3. 使用插件

```python
# 執行指令
result = await plugin_manager.execute_command(
    plugin_name="my_command",
    command_name="custom_action",
    parameters={"speed": "fast", "duration_ms": 5000}
)

print(result["actions"])  # 展開的動作序列
```

## 開發裝置插件

### 1. 建立裝置插件類別

```python
from MCP.plugin_base import (
    DevicePluginBase,
    PluginCapability,
    PluginConfig,
    PluginMetadata,
    PluginType,
)

class MyDevicePlugin(DevicePluginBase):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="my_device",
            version="1.0.0",
            author="Your Name",
            description="自訂裝置驅動",
            plugin_type=PluginType.DEVICE,
            capabilities=PluginCapability(
                supports_streaming=True,
                supports_async=True,
                requires_hardware=True
            )
        )
    
    @property
    def device_type(self) -> str:
        return "custom_device"
    
    async def _on_initialize(self) -> bool:
        """初始化裝置"""
        # 連接硬體、初始化驅動等
        self.logger.info("初始化自訂裝置")
        return True
    
    async def _on_shutdown(self) -> bool:
        """關閉裝置"""
        # 釋放資源、關閉連線等
        self.logger.info("關閉自訂裝置")
        return True
    
    async def read_data(self, **kwargs) -> Dict[str, Any]:
        """讀取裝置資料"""
        # 從硬體讀取資料
        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "value": 42,
            "unit": "units"
        }
        
        return {
            "success": True,
            "device": self.metadata.name,
            "data": data
        }
    
    async def get_device_info(self) -> Dict[str, Any]:
        """取得裝置資訊"""
        return {
            "device_type": self.device_type,
            "status": "online",
            "capabilities": ["read", "write", "stream"]
        }
    
    async def start_stream(self) -> bool:
        """啟動資料串流"""
        self.logger.info("啟動串流")
        # 實作串流邏輯
        return True
    
    async def stop_stream(self) -> bool:
        """停止資料串流"""
        self.logger.info("停止串流")
        # 停止串流
        return True
```

### 2. 使用裝置插件

```python
# 讀取資料
data = await plugin_manager.read_device_data(
    plugin_name="my_device",
    samples=10
)

# 取得裝置資訊
device = plugin_manager.get_device_plugin("my_device")
info = await device.get_device_info()

# 控制串流
await device.start_stream()
# ... 處理串流資料 ...
await device.stop_stream()
```

## 插件配置

### PluginConfig 選項

```python
config = PluginConfig(
    enabled=True,        # 是否啟用插件
    priority=100,        # 優先級（數字越小越優先）
    config={             # 自訂配置
        "device_path": "/dev/video0",
        "resolution": {"width": 640, "height": 480}
    },
    tags=["production", "v1"]  # 標籤
)
```

### 配置 Schema

插件可定義配置 schema 用於驗證：

```python
@property
def metadata(self) -> PluginMetadata:
    return PluginMetadata(
        # ... 其他欄位 ...
        config_schema={
            "type": "object",
            "properties": {
                "device_path": {
                    "type": "string",
                    "description": "裝置路徑",
                    "default": "/dev/video0"
                },
                "resolution": {
                    "type": "object",
                    "properties": {
                        "width": {"type": "integer"},
                        "height": {"type": "integer"}
                    }
                }
            }
        }
    )
```

## API 端點

### 插件管理

```http
GET /api/plugins
GET /api/plugins/health
GET /api/plugins/{plugin_name}/commands
POST /api/plugins/{plugin_name}/execute
```

### 裝置控制

```http
GET /api/devices/{device_name}/info
POST /api/devices/{device_name}/read
```

### 使用範例

```bash
# 列出所有插件
curl http://localhost:8000/api/plugins

# 取得插件健康狀態
curl http://localhost:8000/api/plugins/health

# 取得插件支援的指令
curl http://localhost:8000/api/plugins/advanced_command/commands

# 執行指令
curl -X POST http://localhost:8000/api/plugins/advanced_command/execute \
  -H "Content-Type: application/json" \
  -d '{
    "command_name": "patrol",
    "parameters": {
      "waypoints": [
        {"x": 10, "y": 20},
        {"x": 30, "y": 40}
      ],
      "speed": "normal"
    }
  }'

# 讀取裝置資料
curl -X POST http://localhost:8000/api/devices/camera/read \
  -H "Content-Type: application/json" \
  -d '{
    "format": "jpeg",
    "quality": 85
  }'
```

## 最佳實踐

### 1. 錯誤處理

```python
async def execute_command(self, command_name, parameters, context):
    try:
        # 執行邏輯
        result = await self._do_something(parameters)
        
        return {
            "success": True,
            "result": result
        }
    
    except ValueError as e:
        self.logger.warning(f"參數錯誤: {e}")
        return {
            "success": False,
            "error": f"參數錯誤: {e}"
        }
    
    except Exception as e:
        self.logger.error(f"執行失敗: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }
```

### 2. 日誌記錄

```python
self.logger.info("執行指令", extra={
    "command": command_name,
    "parameters": parameters,
    "trace_id": context.get("trace_id") if context else None
})
```

### 3. 資源管理

```python
async def _on_initialize(self) -> bool:
    """初始化時取得資源"""
    self.resource = await acquire_resource()
    return True

async def _on_shutdown(self) -> bool:
    """關閉時釋放資源"""
    if self.resource:
        await self.resource.close()
    return True
```

### 4. 健康檢查

```python
async def health_check(self) -> Dict[str, Any]:
    """自訂健康檢查"""
    base_health = await super().health_check()
    
    # 加入自訂健康資訊
    base_health.update({
        "device_connected": self._is_connected(),
        "last_read_time": self._last_read_time
    })
    
    return base_health
```

## 測試

### 單元測試範例

```python
import pytest
from MCP.plugin_base import PluginConfig
from my_plugin import MyCommandPlugin

@pytest.mark.asyncio
async def test_plugin_initialization():
    """測試插件初始化"""
    config = PluginConfig(enabled=True)
    plugin = MyCommandPlugin(config)
    
    success = await plugin.initialize()
    assert success is True
    assert plugin.status == PluginStatus.ACTIVE

@pytest.mark.asyncio
async def test_execute_command():
    """測試指令執行"""
    config = PluginConfig(enabled=True)
    plugin = MyCommandPlugin(config)
    await plugin.initialize()
    
    result = await plugin.execute_command(
        command_name="custom_action",
        parameters={"speed": "fast"},
        context={"trace_id": "test-123"}
    )
    
    assert result["success"] is True
    assert "actions" in result
```

## 疑難排解

### 插件無法載入

**問題**：插件註冊失敗

**解決方案**：
1. 檢查插件類別是否正確繼承基底類別
2. 確認所有抽象方法都已實作
3. 查看日誌檔獲取詳細錯誤訊息

### 執行錯誤

**問題**：插件執行時發生錯誤

**解決方案**：
1. 檢查插件狀態是否為 ACTIVE
2. 驗證參數是否符合 schema
3. 確認依賴項是否已載入
4. 查看 error_message 屬性

### 效能問題

**問題**：插件執行緩慢

**解決方案**：
1. 使用 async/await 避免阻塞
2. 考慮批次處理
3. 實作快取機制
4. 檢查是否有資源洩漏

## 擴充範例

### 整合第三方 API

```python
class ThirdPartyAPIPlugin(CommandPluginBase):
    async def _on_initialize(self) -> bool:
        self.api_client = ThirdPartyClient(
            api_key=self.config.config.get("api_key")
        )
        return True
    
    async def execute_command(self, command_name, parameters, context):
        response = await self.api_client.call_api(
            endpoint=command_name,
            data=parameters
        )
        
        return {
            "success": True,
            "result": response
        }
```

### 多裝置協調

```python
class MultiDevicePlugin(DevicePluginBase):
    async def _on_initialize(self) -> bool:
        # 初始化多個子裝置
        self.camera = CameraDevice()
        self.sensor = SensorDevice()
        return True
    
    async def read_data(self, **kwargs) -> Dict[str, Any]:
        # 同時讀取多個裝置
        camera_data = await self.camera.read()
        sensor_data = await self.sensor.read()
        
        return {
            "success": True,
            "camera": camera_data,
            "sensor": sensor_data
        }
```

## 參考資源

- [MCP 模組設計](../MCP/Module.md)
- [LLM 提供商整合指南](MCP_LLM_PROVIDERS.md)
- [API 參考](../MCP/README.md)
- [插件基底類別原始碼](../MCP/plugin_base.py)

## 授權

MIT License
