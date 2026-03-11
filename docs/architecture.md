# Robot Command Console - Architecture Document

## Project Overview

Robot Command Console is a unified platform for managing, routing, and executing robot commands. This document explains the updated folder structure, module responsibilities, and design principles.

> **Status**: Phase 3.2 in progress (Tiny version core structure complete, integration testing ongoing)
> **Last Updated**: 2026-01-28

## Updated Folder Structure (Phase 3)

```
robot-command-console/
├── Cloud/                     # Cloud-based operations
│   ├── MCP/                   # Model Context Protocol services
│   ├── user_management/       # User management services
│   ├── notification/          # Notification services
│   └── firmware_repository/   # Firmware repository
│
├── Edge/                      # Edge computing and services
│   ├── MCP/                   # Unified MCP and LLM discovery module
│   ├── qtwebview-app/         # PyQt application (Tiny version)
│   ├── WebUI/                 # Web-based user interface
│   ├── unified-edge-app/      # Unified edge application
│   └── start_all_services.py  # Script to start all edge services
│
├── Executor/                  # Robot command execution
│   ├── action_executor.py     # Executes robot actions
│   ├── advanced_decoder.py    # Decodes advanced commands
│   ├── pubsub.py              # Publish-subscribe utilities
│   └── tools.py               # Utility tools for execution
│
├── config/                    # Configuration files
├── docs/                      # Documentation
├── tests/                     # Test cases and examples
├── Cloud/requirements.txt     # Cloud Python dependencies
├── Edge/requirements.txt      # Edge Python dependencies
└── Executor/requirements.txt  # Executor Python dependencies
```

## Design Principles

1. **Modular Architecture**: Each module (Cloud, Edge, Executor) is independent and can be developed, tested, and extended separately.
2. **Standardized Contracts**: All communication uses JSON Schema with traceable `trace_id`.
3. **Human Intervention**: WebUI provides complete control and intervention capabilities.
4. **Extensibility**: Adding new robot types or protocols requires minimal changes.
5. **Security and Auditability**: All operations are traceable, sensitive actions require approval, and permissions are strictly managed.

## Module Responsibilities

### Cloud Services

- **MCP/**: Provides a unified API for command reception, validation, routing, authentication, schema verification, context management, LLM integration, and observability.
- **User Management**: Manages users and their permissions.
- **Notification**: Sends notifications to users.
- **Firmware Repository**: Stores and manages firmware versions.

### Edge Services

- **LLM Discovery**: Finds and discovers LLMs.
- **QtWebview App**: Provides a GUI for the Tiny version.
- **WebUI**: Provides a web-based user interface.
- **Unified Edge App**: A single application to manage all edge services.

### Executor Services

- **Action Executor**: Executes robot actions.
- **Advanced Decoder**: Decodes advanced commands.
- **Pub/Sub Utilities**: Publishes and subscribes to events.
- **Utility Tools**: Provides tools for execution.

## Data Flow

```
Users → WebUI → MCP API → Command Handler
                                              ↓
                                        Robot Router
                                              ↓
                    ← Response ← Robot-Console ← MQTT/HTTP
```

## Future Architecture: Cloud-Edge-Runner (Phase 2+ Evolution)

> **🚀 Evolution Direction**: The project will evolve into **Cloud-Edge-Runner** three-tier architecture based on the proposal.md design.

### Architecture Overview (Consistent with proposal.md)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Cloud / Server Layer                             │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                        Cloud Services                               │ │
│  │  • 進階指令共享與排名                                                │ │
│  │  • 用戶討論區                                                       │ │
│  │  • 用戶授權與信任評級                                                │ │
│  │  • 共享 LLM 分析服務（大數據優化）                                   │ │
│  │  • 固件倉庫                                                         │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                          HTTPS/WSS （當網路可用時）
                                    │
┌─────────────────────────────────────────────────────────────────────────┐
│                      Edge Layer (ALL-in-One Edge App)                    │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                     Unified Launcher                                │ │
│  │  一鍵啟動/停止所有服務 | LLM 選擇介面 | 系統健康監控                 │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐        │
│  │   Local WebUI    │ │   MCP Service    │ │   Robot Service  │        │
│  │  • 用戶設定介面  │ │  • 指令協調      │ │  • 本地佇列      │        │
│  │  • 機器人監控   │ │  • LLM 處理器    │ │  • Worker Pool   │        │
│  │  • 固件更新     │ │  • 插件系統      │ │  • 離線緩衝      │        │
│  └──────────────────┘ └──────────────────┘ └──────────────────┘        │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                    Local LLM Provider                               │ │
│  │                 (Ollama / LM Studio / Cloud fallback)               │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                          Hardware Interface
                                    │
┌─────────────────────────────────────────────────────────────────────────┐
│                          Runner Layer                                    │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                     Robot-Console                                   │ │
│  │  • 動作執行器（ActionExecutor）                                     │ │
│  │  • 協定適配（HTTP/MQTT/WS/Serial/ROS）                              │ │
│  │  • 緊急停止與安全機制                                               │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │  Humanoid   │  │     AGV     │  │    Drone    │  │     Arm     │    │
│  │   robot_7   │  │   robot_3   │  │   robot_9   │  │   robot_12  │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

### Tier Responsibilities

| Tier | Directory | Responsibility |
|------|-----------|-----------------|
| **Cloud/Server** | Cloud-based services | Cloud services for shared resources and advanced features |
| **Edge** | `src/robot_service/`, `electron-app/`, `MCP/`, `WebUI/` | Local processing, queuing, LLM, monitoring |
| **Runner** | `Robot-Console/` | Action execution, hardware control, safety mechanisms |
| **Common** | `src/common/` | Logging, time, configuration tools |

#### Cloud/Server Layer (Cloud-based services)
- **進階指令共享與排名**：Communities share advanced commands
- **用戶討論區**：Experience sharing platform
- **用戶授權與信任評級**：Centralized authentication
- **共享 LLM 分析服務**：Big data optimized AI services
- **固件倉庫**：Centralized firmware version management

#### Edge Layer (Edge computing and services)
- **本地處理**：Low-latency command execution, offline support
- **本地佇列**：Priority queues, retry mechanisms
- **LLM 處理器**：Local LLM inference (Ollama/LM Studio)
- **插件系統**：Extensible functional modules
- **狀態同步**：Regular synchronization with Cloud

#### Runner Layer (Execution layer)
- **動作執行**：Direct control of robots
- **感測器整合**：Collecting robot states
- **安全機制**：Emergency stop, boundary checks
- **協定支援**：HTTP/MQTT/WS/Serial/ROS

### Data Flow (Consistent with proposal.md)

1. **指令下達**：User → Edge WebUI → MCP (LLM parsing) → Robot Service (Queue) → Robot-Console → Robot
2. **狀態回報**：Robot → Robot-Console → Robot Service → Edge WebUI (Real-time display)
3. **雲端同步**：Edge ↔ Cloud (Advanced commands, user settings, analysis data)
4. **審計追蹤**：All operations → Local event logs (with trace_id) → Optional upload to Cloud

### Phase 3.1 Completed Features

- [x] **統一啟動器**（`unified_launcher.py`）：One-key start/stop all services
- [x] **服務協調器**（`service_coordinator.py`）：Service lifecycle management, health checks, automatic restart
- [x] **共享狀態管理器**（`shared_state.py`）：Service inter-state sharing, event notifications
- [x] **本地狀態存儲**（`state_store.py`）：SQLite persistence, TTL expiry support
- [x] **事件匯流排**（`event_bus.py`）：Pub/Sub event communication

### Phase 3.2+ Plans

- [ ] **WebUI 本地版**：Complete Edge user interface
- [x] **固件更新介面**：Robot firmware management (UI/API complete)
- [ ] **離線模式支援**：Core functionality without network
- [x] **CLI/TUI 版本**：Terminal interface support (✅ Complete)
- [ ] **雲端服務整合**：Advanced command sharing, discussion, authorization
- [ ] **分散式佇列**：Redis/Kafka integration
- [ ] **多節點部署**：Kubernetes support

## Future Expansion (Phase 3.2+)

- [ ] Cloud-Edge-Runner architecture complete implementation
- [ ] Redis/Kafka integration (distributed queue)
- [ ] Kubernetes deployment
- [ ] More robot types support
- [ ] Advanced analysis and reporting
- [ ] Multi-tenant support

## References

- [README.md](../README.md) - Project overview and quick start
- [proposal.md](proposal.md) - Authority specification
- [PROJECT_MEMORY.md](PROJECT_MEMORY.md) - Project memory and lessons learned
- [observability.md](features/observability-guide.md) - Observability guide
- [queue-architecture.md](features/queue-architecture.md) - Queue architecture details
- [Robot Service README](../src/robot_service/README.md) - Robot Service explanation
- [MCP Module](../MCP/Module.md) - MCP Module design
- [Robot-Console Module](../Robot-Console/module.md) - Robot-Console design
- [Python Lint Guide](development/PYTHON_LINT_GUIDE.md) - Code style and lint repair strategies
- [Phase 3.1 Status Report](phase3/PHASE3_1_STATUS_REPORT.md) - Phase 3.1 completion summary

## Version History

- **Phase 1** - Initial implementation, functional completeness (Completed)
- **Phase 2** - Directory restructuring, modular clarity (Completed)
- **Phase 3.1** - Foundation integration: Unified launcher, service coordinator, shared state (Completed)
- **Phase 3.2** - Functional enhancement: WebUI local version, offline mode, CLI/TUI (In progress - TUI complete)
