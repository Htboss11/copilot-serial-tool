# Daemon-Based Architecture - Serial Monitor Extension v2.0

## Overview

The Serial Monitor extension now uses a **persistent Python daemon** architecture for robust, continuous serial monitoring with SQLite data storage and MCP integration.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    VS Code Extension                         │
│  - Extension Host (TypeScript)                               │
│  - MCP Server Provider                                       │
└───────────────────────┬─────────────────────────────────────┘
                        │ stdio
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              MCP Server (Python)                             │
│  - daemon/mcp_server.py                                      │
│  - JSON-RPC Protocol Handler                                 │
│  - 8 MCP Tools Exposed                                       │
└───────────────────────┬─────────────────────────────────────┘
                        │ Python API
                        ▼
┌─────────────────────────────────────────────────────────────┐
│           Daemon Control Tools (Python)                      │
│  - daemon/mcp_daemon_tools.py                                │
│  - Start/Stop/Status/Connect/Disconnect                      │
│  - Query/Recent/Tail Data                                    │
└───────────────────────┬─────────────────────────────────────┘
                        │ JSON Command Files
                        ▼
┌─────────────────────────────────────────────────────────────┐
│         Serial Daemon (Background Process)                   │
│  - daemon/serial_daemon.py                                   │
│  - Singleton (file lock protected)                           │
│  - Polls for commands every 100ms                            │
│  - Runtime connect/disconnect support                        │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┴────────────────┐
        ▼                                ▼
┌──────────────────┐          ┌──────────────────┐
│  Serial Handler  │          │  Database Mgr    │
│  - Reconnect     │          │  - SQLite DB     │
│  - USB unplug    │          │  - WAL mode      │
│  - Timeout       │          │  - Batched write │
└────────┬─────────┘          └────────┬─────────┘
         │                              │
         ▼                              ▼
    Serial Port                  ~/.serial-monitor/
    (Hardware)                   serial_data.db
```

## Core Components

### 1. **Serial Daemon** (`daemon/serial_daemon.py`)
- **Type**: Background Process (Singleton)
- **Lifecycle**: Starts with VS Code, runs continuously
- **State Management**:
  - `running`: Daemon process alive
  - `monitoring`: Currently connected to serial port
- **Key Features**:
  - File lock prevents multiple instances
  - Polls command files every 100ms
  - Runtime port connect/disconnect
  - Automatic reconnection on USB unplug
  - Health checks and crash recovery
  - SQLite data capture

### 2. **Database Manager** (`daemon/db_manager.py`)
- **Type**: Data Persistence Layer
- **Storage**: SQLite with WAL mode
- **Schema**:
  ```sql
  CREATE TABLE serial_data (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      timestamp TEXT NOT NULL,
      port TEXT NOT NULL,
      data TEXT NOT NULL,
      session_id TEXT NOT NULL
  )
  ```
- **Features**:
  - Batched writes (100 lines)
  - Automatic flush on timeout (5s)
  - Corruption recovery
  - Time-based and port-based indexes

### 3. **Command Interface** (`daemon/daemon_commands.py`)
- **Type**: Inter-Process Communication
- **Protocol**: JSON files
- **Files**:
  - `~/.serial-monitor/daemon_command.json` (client → daemon)
  - `~/.serial-monitor/daemon_response.json` (daemon → client)
- **Commands**: connect, disconnect, status
- **Timeout**: 5 seconds

### 4. **MCP Server** (`daemon/mcp_server.py`)
- **Type**: AI Agent Interface
- **Protocol**: JSON-RPC 2.0 over stdio
- **Transport**: Standard input/output
- **Tools Exposed**: 8 daemon control tools
- **Integration**: GitHub Copilot via MCP

### 5. **Daemon Manager** (`daemon/daemon_manager.py`)
- **Type**: Process Lifecycle Management
- **Features**:
  - PID file management
  - File lock (Windows msvcrt / Unix fcntl)
  - Stale process detection
  - Health checks

### 6. **Serial Handler** (`daemon/serial_handler.py`)
- **Type**: Serial Port Communication
- **Features**:
  - Automatic reconnection (5 attempts)
  - USB unplug detection
  - Timeout handling
  - Line-based reading
  - Data buffering

#### 6. **Python Script** (`python/serial_monitor.py`)
- **Type**: One-shot Serial Operations
- **Current Inputs**: CLI args
- **Current Outputs**: JSON to stdout
- **Status**: KEEP - Still useful for spawned operations

## Unified Architecture Design

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     VS Code Extension                        │
│                                                              │
│  ┌──────────────┐         ┌─────────────────────────────┐  │
│  │ UI Commands  │────────▶│                             │  │
│  └──────────────┘         │   Unified Serial Manager    │  │
│                           │                             │  │
│  ┌──────────────┐         │  - Connection Management    │  │
│  │  MCP Server  │────────▶│  - Background Monitoring    │  │
│  │  (Copilot)   │         │  - Data Buffering          │  │
│  └──────────────┘         │  - Auto-reconnect          │  │
│                           │                             │  │
│                           └────────┬────────────────────┘  │
│                                    │                        │
│                           ┌────────▼────────────────────┐  │
│                           │   Session Manager           │  │
│                           │  - File logging             │  │
│                           │  - Buffered writes          │  │
│                           │  - Session lifecycle        │  │
│                           └────────┬────────────────────┘  │
│                                    │                        │
└────────────────────────────────────┼────────────────────────┘
                                     │
                           ┌─────────▼──────────┐
                           │  Python Helper     │
                           │  (pyserial)        │
                           │  - Port listing    │
                           │  - Serial I/O      │
                           └────────────────────┘
```

### Component Interfaces

#### **SerialManager (Enhanced)**

```typescript
interface SerialManager {
  // Inputs
  - listPorts(): Promise<SerialPortInfo[]>
  - connect(port: string, baudRate: number): Promise<ConnectionResult>
  - disconnect(port: string): Promise<Result>
  - send(port: string, data: string): Promise<Result>
  - read(port: string, duration: number): Promise<ReadResult>
  - getBuffer(port: string, seconds?: number): Promise<BufferResult>
  
  // Internal State
  - connections: Map<string, ActiveConnection>
  - buffers: Map<string, CircularBuffer>
  - monitoring: Map<string, MonitoringTask>
  
  // Outputs
  - OutputChannel updates (UI)
  - SessionManager calls (logging)
  - Data buffers (for read operations)
}

interface ActiveConnection {
  port: string
  baudRate: number
  process: ChildProcess
  buffer: CircularBuffer
  sessionStarted: Date
  monitoring: boolean
}

class CircularBuffer {
  private data: Array<{timestamp: string, line: string}>
  private maxSeconds: number
  
  add(timestamp: string, line: string): void
  getAll(): Array<{timestamp: string, line: string}>
  getRecent(seconds: number): Array<{timestamp: string, line: string}>
  clear(): void
}
```

#### **MCP Server (Simplified)**

```typescript
interface MCPServer {
  // Inputs (from GitHub Copilot)
  - initialize request
  - tools/list request
  - tools/call request
  
  // Internal (uses SerialManager)
  - serialManager: SerialManager
  
  // Outputs (to GitHub Copilot)
  - MCP JSON-RPC responses
}
```

#### **SessionManager (Unchanged)**

```typescript
interface SessionManager {
  // Inputs
  - startSession(portPath: string): void
  - endSession(): void
  - logData(portPath: string, timestamp: string, data: string): void
  
  // Outputs
  - Log files in serial-sessions/
  - Buffered file writes
}
```

## Implementation Strategy

### Phase 1: Enhance SerialManager

1. **Add CircularBuffer class** to SerialManager
   - Store last 600 seconds of data
   - Thread-safe operations
   - Time-based expiry

2. **Add persistent connection management**
   - Keep Python processes alive
   - Monitor stdout continuously
   - Auto-reconnect on process exit

3. **Add getBuffer method**
   - Return buffered data
   - Support time filtering

4. **Integrate with SessionManager properly**
   - Log all captured data
   - Include connection markers
   - Proper session lifecycle

### Phase 2: Update MCP Server

1. **Remove TCP socket communication**
2. **Add SerialManager dependency injection**
3. **Update tool handlers to use SerialManager methods**
4. **Ensure proper error handling and responses**

### Phase 3: Clean Up

1. **Remove serial_server.py**
2. **Remove TCP server code**
3. **Update tests**
4. **Update documentation**

## Success Criteria

✅ Single code path for both UI and MCP operations
✅ All data logged to session files
✅ CircularBuffer maintains last 10 minutes
✅ Auto-reconnect works on device reset
✅ Connection markers in logs
✅ MCP tools work with GitHub Copilot
✅ UI commands still work
✅ No duplicate logging or monitoring

## Risk Mitigation

- Keep existing UI functionality working
- Test each component independently
- Maintain backwards compatibility with settings
- Clear error messages for debugging
