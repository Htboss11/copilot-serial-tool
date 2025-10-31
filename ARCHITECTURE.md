# Unified Architecture Design - Serial Monitor Extension

## Current State Analysis

### Component Inventory

#### 1. **Extension Entry Point** (`src/extension.ts`)
- **Type**: VS Code Extension Host
- **Inputs**: VS Code activation events, user commands
- **Outputs**: Command registrations, MCP server registration
- **Keep/Modify**: KEEP - minimal changes needed

#### 2. **Serial Manager** (`src/serialManager.ts`)
- **Type**: Business Logic Layer
- **Current Inputs**: 
  - Python script path
  - Workspace root
  - Commands from UI
- **Current Outputs**:
  - Spawns Python processes
  - Manages OutputChannels
  - Interfaces with SessionManager
- **Status**: MODIFY - Core of new architecture

#### 3. **Session Manager** (`src/sessionManager.ts`)
- **Type**: Data Persistence Layer
- **Current Inputs**:
  - Port path
  - Timestamp + data
  - Session lifecycle events
- **Current Outputs**:
  - Log files in serial-sessions/
  - Buffered writes with configurable intervals
- **Status**: KEEP - works well, just needs proper integration

#### 4. **MCP Server** (`src/mcp-server-pure.ts`)
- **Type**: AI Agent Interface (JSON-RPC over stdio)
- **Current Inputs**:
  - MCP protocol messages from GitHub Copilot
  - Tool call requests (list_ports, connect, read, etc.)
- **Current Outputs**:
  - MCP responses
  - Commands to Python TCP server
- **Status**: MODIFY - Change to use SerialManager instead of TCP

#### 5. **Python TCP Server** (`python/serial_server.py`)
- **Type**: Persistent Serial Connection Manager
- **Current Inputs**: JSON commands over TCP socket
- **Current Outputs**: JSON responses, log files, circular buffer
- **Status**: REMOVE - Replaced by unified TypeScript solution

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
