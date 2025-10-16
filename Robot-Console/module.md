# Humanoid Folder Description

The **`humanoid`** folder contains a Python-based robot control system designed to control humanoid robots via AWS IoT MQTT messaging. Here's a comprehensive breakdown:

## 📁 **Core Components**

### **1. `action_executor.py`** (311 lines)
The main action execution engine that manages robot movements and commands.

**Key Features:**
- **Action Dictionary**: Contains 38+ predefined robot actions including:
  - **Movement**: `go_forward`, `back_fast`, `left_move_fast`, `right_move_fast`, `turn_left`, `turn_right`
  - **Combat**: `kung_fu`, `wing_chun`, `left_kick`, `right_kick`, `left_uppercut`, `right_uppercut`
  - **Exercises**: `push_ups`, `sit_ups`, `squat`, `chest`, `weightlifting`
  - **Dances**: `dance_two` through `dance_ten` (multiple choreographed routines)
  - **Gestures**: `bow`, `wave`, `stand`, `twist`
  - **Control**: `stop`, `stand_up_front`, `stand_up_back`

- **ActionExecutor Class**:
  - Threaded queue-based action execution system
  - Sends commands to both local robot controller (localhost:9030) and remote simulator
  - Manages action timing and sequential execution
  - Supports immediate stop functionality
  - Handles action interruption and queue management

### **2. `pubsub.py`** (263 lines)
AWS IoT Core MQTT publish-subscribe client for receiving remote commands.

**Key Features:**
- **PubSubClient Class**: Manages MQTT connection lifecycle
- **Dual Connection Mode**: Supports both mTLS (mutual TLS) and WebSocket connections
- **Auto-fallback**: Tries mTLS first, falls back to WebSocket if failed
- **Message Handler**: Receives JSON payloads with `toolName` field and queues actions
- **AWS Credential Management**: Loads from environment variables, config files, or AWS CLI credentials
- **Topic Subscription**: Listens on `{robot_name}/topic` pattern

### **3. `tools.py`** (201 lines)
Tool and action definitions for external integrations (likely for LLM/AI agents).

**Key Features:**
- Duplicates action definitions from `action_executor.py`
- **TOOL_LIST**: Human-readable descriptions of all 38 robot actions
- **TOOLS**: Formatted tool specifications with JSON schema for AI/LLM integration
- Enables natural language command interpretation

### **4. `settings.yaml`**
Configuration file for robot and AWS IoT settings.

**Configuration:**
- `robot_name`: "robot_7" (configurable robot identifier)
- AWS IoT endpoint and credentials
- Certificate paths for mTLS authentication
- Session key for simulator authentication
- Simulator endpoint URL (AWS App Runner hosted)

### **5. `requirements.txt`**
Python dependencies:
- `awsiotsdk`: AWS IoT SDK for MQTT connectivity
- `pyyaml`: YAML configuration parsing
- `requests`: HTTP requests to simulator and robot controller
- Commented out: audio, AWS Bedrock, boto3 (future features?)

## 🛠️ **Utility Scripts**

### **6. `create_virtual_env.sh`**
Bash script to set up Python virtual environment and install dependencies.

### **7. `create_deploy_package.sh`**
Creates a deployment package (`deploy_package.zip`) excluding virtual environment and cache files.

### **8. `AmazonRootCA1.pem`**
Amazon root CA certificate for secure AWS IoT TLS connections.

---

## 🔄 **System Architecture**

```
AWS IoT Core (MQTT)
        ↓ (publishes action commands)
   pubsub.py (subscriber)
        ↓ (queues actions)
  ActionExecutor
        ↓ (sends commands in parallel)
        ├→ Local Robot Controller (localhost:9030)
        └→ Remote Simulator (AWS App Runner)
```

## 🎯 **Use Cases**
1. **Remote Robot Control**: Control physical humanoid robots via cloud messaging
2. **Simulator Integration**: Test actions in a web-based simulator before deploying to hardware
3. **AI/LLM Integration**: The tools.py enables natural language control through AI agents
4. **Multi-robot Support**: Configuration-based robot identification for fleet management

This is a production-ready IoT robotics control system with robust error handling, dual-mode connectivity, and integration points for AI-driven control!
