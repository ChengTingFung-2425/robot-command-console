# Documentation Index

## Core Documents

| Document | Description |
|----------|-------------|
| [`proposal.md`](proposal.md) | **Authoritative Specification**: Project goals, architecture, modules, data contracts, implementation paths |
| [`architecture.md`](architecture.md) | Folder structure, Edge/Server separation, module responsibilities |
| [`PROJECT_MEMORY.md`](PROJECT_MEMORY.md) | Architecture decisions, shared tools, and lessons learned |

---

## Folder Structure

### 📂 Cloud/
- **Purpose**: Cloud-based operations
- **Key Modules**: MCP, user management, notifications, firmware repository

### 📂 Edge/
- **Purpose**: Edge computing and services
- **Key Modules**: llm_discovery, qtwebview-app, WebUI, unified-edge-app

### 📂 Executor/
- **Purpose**: Robot command execution
- **Key Modules**: action_executor, advanced_decoder, pubsub, tools

### 📂 config/
- **Purpose**: Configuration files

### 📂 tests/
- **Purpose**: Test cases and examples

### 📂 docs/
- **Purpose**: Documentation

---

## Plans

| Document | Description |
|----------|-------------|
| [`MASTER_PLAN.md`](plans/MASTER_PLAN.md) | Phase 0-6 complete plan |
| [`PHASE3_EDGE_ALL_IN_ONE.md`](plans/PHASE3_EDGE_ALL_IN_ONE.md) | Phase 3 ALL-in-One Edge App plan |

---

## Phase 1 (Electron POC)

| Document | Description |
|----------|-------------|
| [`PHASE1_INDEX.md`](phase1/PHASE1_INDEX.md) | Phase 1 files index |
| [`PHASE1_README.md`](phase1/PHASE1_README.md) | Phase 1 overview |
| [`PHASE1_COMPLETE.md`](phase1/PHASE1_COMPLETE.md) | Phase 1 completion report |
| [`electron-testing-guide.md`](phase1/electron-testing-guide.md) | Electron testing guide |

---

## Phase 2 (Modularization)

| Document | Description |
|----------|-------------|
| [`PHASE2_COMPLETION_SUMMARY.md`](phase2/PHASE2_COMPLETION_SUMMARY.md) | Phase 2 completion summary |
| [`MIGRATION_GUIDE_PHASE2.md`](phase2/MIGRATION_GUIDE_PHASE2.md) | Phase 2 migration guide |
| [`robot-service-migration.md`](phase2/robot-service-migration.md) | Robot Service migration |
| [`ADVANCED_COMMAND_RESPONSIBILITY_CHANGE.md`](phase2/ADVANCED_COMMAND_RESPONSIBILITY_CHANGE.md) | Advanced command responsibility change |

---

## Phase 3 (ALL-in-One Edge App)

| Document | Description |
|----------|-------------|
| [`PHASE3_1_STATUS_REPORT.md`](phase3/PHASE3_1_STATUS_REPORT.md) | Phase 3.1 status report and lessons learned |
| [`TEST_PLAN_PHASE3_1.md`](phase3/TEST_PLAN_PHASE3_1.md) | Phase 3.1 test plan |

---

## User Guides

| Document | Description |
|----------|-------------|
| [`USER_GUIDE_INDEX.md`](user_guide/USER_GUIDE_INDEX.md) | **User Guide Index** - Complete navigation |
| [`QUICK_START.md`](user_guide/QUICK_START.md) | **Quick Start Guide** - 5-minute quick start |
| [`INSTALLATION_GUIDE.md`](user_guide/INSTALLATION_GUIDE.md) | **Complete Installation Guide** - All versions, including latest updates 🆕 |
| [`FAQ.md`](user_guide/FAQ.md) | **Common Questions and Answers** - 30+ Q&A |
| [`TROUBLESHOOTING.md`](user_guide/TROUBLESHOOTING.md) | **Troubleshooting Guide** - Problem diagnosis and solutions |
| [`FEATURES_REFERENCE.md`](user_guide/FEATURES_REFERENCE.md) | **Feature Complete Reference** - All features detailed description |
| [`WEBUI_USER_GUIDE.md`](user_guide/WEBUI_USER_GUIDE.md) | **WebUI User Guide** - Web interface operations |
| [`TUI_USER_GUIDE.md`](user_guide/TUI_USER_GUIDE.md) | TUI User Guide - Terminal interface operations |
| [`TINY_VS_HEAVY.md`](user_guide/TINY_VS_HEAVY.md) | Heavy/Tiny version selection guide |
| [`TINY_INSTALL_GUIDE.md`](user_guide/TINY_INSTALL_GUIDE.md) | Tiny version installation guide |

### 📁 user_guide/
Users guides

| Document | Description |
|----------|-------------|
| [`TINY_VS_HEAVY.md`](user_guide/TINY_VS_HEAVY.md) | Heavy/Tiny version selection guide |
| [`TINY_INSTALL_GUIDE.md`](user_guide/TINY_INSTALL_GUIDE.md) | Tiny version installation guide |
| [`TUI_USER_GUIDE.md`](user_guide/TUI_USER_GUIDE.md) | TUI User Guide - Terminal interface operations |

### 📁 development/
Development guidelines and best practices

| Document | Description |
|----------|-------------|
| [`PYTHON_LINT_GUIDE.md`](development/PYTHON_LINT_GUIDE.md) | Python code style and lint repair strategies |
| [`STARTUP_RECOVERY_GUIDE.md`](development/STARTUP_RECOVERY_GUIDE.md) | Service startup exception recovery guide |
| [`UNIFIED_LAUNCHER_GUIDE.md`](development/UNIFIED_LAUNCHER_GUIDE.md) | Unified launcher usage guide |

### 📁 mcp/
MCP (Model Context Protocol) related documents

| Document | Description |
|----------|-------------|
| [`MCP_LLM_PROVIDERS.md`](mcp/MCP_LLM_PROVIDERS.md) | LLM provider integration guide |
| [`MCP_PLUGIN_ARCHITECTURE.md`](mcp/MCP_PLUGIN_ARCHITECTURE.md) | Plugin architecture design |

### 📁 security/
Security related documents

| Document | Description |
|----------|-------------|
| [`api-security-guide.md`](security/api-security-guide.md) | API security guide |
| [`API_SECURITY_IMPLEMENTATION_SUMMARY.md`](security/API_SECURITY_IMPLEMENTATION_SUMMARY.md) | Security implementation summary |
| [`security-checklist.md`](security/security-checklist.md) | Security checklist |
| [`threat-model.md`](security/threat-model.md) | Threat model analysis |
| [`password-reset-implementation.md`](security/password-reset-implementation.md) | Password reset implementation |

### 📁 features/
Feature implementation documents

| Document | Description |
|----------|-------------|
| [`observability-guide.md`](features/observability-guide.md) | Observability guide |
| [`observability-implementation.md`](features/observability-implementation.md) | Observability implementation summary |
| [`queue-architecture.md`](features/queue-architecture.md) | Queue architecture design |
| [`user-engagement-system.md`](features/user-engagement-system.md) | User engagement system |
| [`media-streaming-feature.md`](features/media-streaming-feature.md) | Media streaming feature |
| [`webui-testing-guide.md`](features/webui-testing-guide.md) | WebUI testing guide |

### 📁 contract/
JSON Schema definitions

| Document | Description |
|----------|-------------|
| [`command_request.schema.json`](contract/command_request.schema.json) | Command request Schema |
| [`command_response.schema.json`](contract/command_response.schema.json) | Command response Schema |
| [`event_log.schema.json`](contract/event_log.schema.json) | Event log Schema |
| [`error.schema.json`](contract/error.schema.json) | Error format Schema |

---

## Quick Navigation

- **Getting Started**: [`proposal.md`](proposal.md) → [`architecture.md`](architecture.md)
- **User Guide**: [`user_guide/`](user_guide/) - Version selection, installation, TUI usage
- **Phase Status**: [`plans/MASTER_PLAN.md`](plans/MASTER_PLAN.md)
- **Phase 3**: [`plans/PHASE3_EDGE_ALL_IN_ONE.md`](plans/PHASE3_EDGE_ALL_IN_ONE.md) → [`phase3/PHASE3_1_STATUS_REPORT.md`](phase3/PHASE3_1_STATUS_REPORT.md)
- **Development Guide**: [`development/`](development/)
- **Security**: [`security/`](security/)
- **MCP/LLM**: [`mcp/`](mcp/)
- **Testing**: [`phase1/electron-testing-guide.md`](phase1/electron-testing-guide.md)、[`features/webui-testing-guide.md`](features/webui-testing-guide.md)

---

**Last Updated**: 2025-12-22
