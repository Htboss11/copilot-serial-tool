# Release Notes - Version 1.2.1

## ✅ All Requested Features Implemented and Fixed

### 1. **CircularBuffer for Data Storage**
- ✅ Stores last **600 seconds (10 minutes)** of serial data by default
- ✅ Thread-safe implementation using `collections.deque` with locks
- ✅ Automatic cleanup of expired data based on timestamps
- ✅ Configurable retention period via optional `buffer_seconds` parameter
- **Location**: `python/serial_server.py` - `CircularBuffer` class (lines 23-74)

### 2. **Automatic Reconnection**
- ✅ Monitors serial connection in background thread
- ✅ Automatically reconnects when device disconnects (e.g., Raspberry Pi Pico reset)
- ✅ **2-second delay** between reconnection attempts to allow device initialization
- ✅ Preserves buffer across reconnections
- ✅ Non-blocking - doesn't hang on connection attempts
- **Location**: `python/serial_server.py` - `_monitor_with_reconnect()` method (lines 146-209)

### 3. **Connection State Markers**
- ✅ **CONNECTION ESTABLISHED** - When initial connection succeeds
- ✅ **CONNECTION LOST** - When device disconnects unexpectedly
- ✅ **CONNECTION RESTORED** - When automatic reconnection succeeds
- ✅ **DISCONNECTED BY USER** - When user explicitly disconnects
- ✅ All markers include timestamps and are stored in buffer
- **Location**: `python/serial_server.py` - Markers added in `connect()`, `disconnect()`, and `_monitor_with_reconnect()` methods

### 4. **get_buffer Tool Implementation**
- ✅ **Python Server**: `get_buffer` command retrieves buffered data with optional time filtering
- ✅ **TypeScript MCP Server**: `getBuffer()` method sends socket command (lines 308-319)
- ✅ **Package.json**: `serial_monitor_get_buffer` tool definition with rich modelDescription
- ✅ Optional `seconds` parameter to filter recent data (e.g., last 30 seconds)
- ✅ Returns array of timestamped entries including connection markers
- **Locations**: 
  - Python: `python/serial_server.py` - `get_buffer()` method (lines 264-288)
  - TypeScript: `src/mcp-server-pure.ts` - `getBuffer()` method (lines 308-319)
  - Package: `package.json` - Tool definition (lines 119-142)

### 5. **Bug Fixes**
- ✅ Fixed timestamp filtering in `get_buffer` - now properly parses ISO format timestamps
- ✅ Changed from tuple iteration `(ts, line)` to dict filtering with `entry['timestamp']`
- ✅ Uses `datetime.fromisoformat()` for accurate timestamp comparison

## Architecture Summary

### Persistent Server Model
- **Python TCP Server** (`serial_server.py`) runs on port 55556
- Maintains connections across multiple MCP tool calls
- Each port has its own:
  - Serial connection object
  - CircularBuffer instance (600-second retention)
  - Background monitoring thread with auto-reconnect

### MCP Tool Integration
- **VS Code Extension** registers as MCP server via `McpServerDefinitionProvider`
- **GitHub Copilot** can use 5 tools:
  1. `serial_monitor_list_ports` - List available ports
  2. `serial_monitor_connect` - Connect to port (starts buffer & monitoring)
  3. `serial_monitor_send` - Send data to device
  4. `serial_monitor_read` - Read for specified duration
  5. `serial_monitor_get_buffer` - Retrieve buffered historical data

### Session Logging
- Background logging with configurable flush intervals (0-60 seconds)
- Setting: `serial-monitor.sessionFlushInterval`
- Default: 2 seconds (balances performance vs data safety)
- Logs stored in `serial-sessions/` directory

## Testing Checklist

To verify all features work correctly:

1. **Connect to Device**
   - AI: "Connect to COM9 at 115200 baud"
   - Verify: CONNECTION ESTABLISHED marker appears

2. **Read Data**
   - AI: "Read from COM9 for 5 seconds"
   - Verify: Timestamped data displayed

3. **Check Buffer**
   - AI: "Get buffer from COM9"
   - Verify: Shows all historical data with timestamps and markers

4. **Test Auto-Reconnect**
   - Unplug/replug Raspberry Pi Pico (or press reset)
   - Wait 2-3 seconds
   - AI: "Get buffer from COM9"
   - Verify: Shows CONNECTION LOST → CONNECTION RESTORED markers
   - Verify: Data continues after reconnection

5. **Time Filtering**
   - AI: "Get last 30 seconds from COM9 buffer"
   - Verify: Only recent entries returned

6. **Clean Disconnect**
   - AI: "Disconnect from COM9"
   - AI: "Get buffer from COM9"
   - Verify: DISCONNECTED BY USER marker appears (without LOST/RESTORED)

## Implementation Statistics

- **Lines of Code**: ~360 lines in `serial_server.py`
- **Buffer Size**: 600 seconds = 10 minutes = ~600-1800 entries (depends on device output rate)
- **Reconnect Delay**: 2 seconds
- **Monitoring Thread**: Daemon thread, auto-terminates on disconnect
- **Port**: TCP 55556 (localhost only, not exposed to network)

## Version History

- **1.2.1** (Current) - Fixed timestamp filtering bug in get_buffer
- **1.2.0** - Added CircularBuffer, auto-reconnect, connection markers, get_buffer tool
- **1.1.0** - Added buffered session logging
- **1.0.9** - Fixed parameter passing, added read command
- **1.0.8** - Fixed MCP protocol handshake
- **1.0.7** - Proper MCP registration via McpServerDefinitionProvider
- **1.0.6** - Initial MCP server implementation
- **1.0.5** - Dependency management (Python/pyserial auto-check)

## Known Limitations

1. **Auto-Approval**: VS Code security model requires user consent for hardware access tools. Auto-approval not possible via settings.
2. **Windows COM Port Lock**: Only one process can open a COM port at a time (OS limitation).
3. **Buffer Memory**: Default 600 seconds = ~10MB for high-frequency devices. Configurable if needed.

## Next Steps

Extension is now production-ready with all requested features. Possible future enhancements:
- Configurable buffer size via settings
- Export buffer to file
- Pattern matching/filtering in buffer
- Multi-device concurrent monitoring
