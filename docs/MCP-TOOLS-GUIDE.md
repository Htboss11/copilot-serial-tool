# VS Code Serial Monitor MCP Tools

This extension provides MCP (Model Context Protocol) tools for AI agents like GitHub Copilot to interact with serial devices programmatically.

## 🔧 Available MCP Tools

### Core Connection Tools

#### `serial_monitor_connect`
Connect to a serial port with optional auto-detection.

**Parameters:**
- `port` (string): Serial port path (e.g., "COM9") or "auto" to detect Pico
- `baud_rate` (number, optional): Baud rate (default: 115200)

**Example:**
```json
{
  "tool": "serial_monitor_connect",
  "parameters": {
    "port": "auto",
    "baud_rate": 115200
  }
}
```

#### `serial_monitor_send`
Send data to connected serial device.

**Parameters:**
- `port` (string): Serial port path or "auto"
- `data` (string): Data to send

**Example:**
```json
{
  "tool": "serial_monitor_send", 
  "parameters": {
    "port": "COM9",
    "data": "help\\n"
  }
}
```

#### `serial_monitor_read`
Read data from serial port for specified duration.

**Parameters:**
- `port` (string): Serial port path or "auto"  
- `duration` (number): Duration in seconds to read
- `timeout` (number, optional): Timeout in milliseconds

**Example:**
```json
{
  "tool": "serial_monitor_read",
  "parameters": {
    "port": "auto",
    "duration": 5
  }
}
```

### Discovery and Information Tools

#### `serial_monitor_list_ports`
List all available serial ports.

**Parameters:** None

**Returns:** Array of available serial ports with details including path, description, manufacturer, VID/PID

#### `serial_monitor_session_info`
Get information about current and historical sessions.

**Parameters:** None

**Returns:**
- Current session status
- Session file information  
- Configuration settings

### Background Monitoring Tools

#### `serial_monitor_start_async`
Start background monitoring with pattern matching.

**Parameters:**
- `port` (string): Serial port path or "auto"
- `watch_for` (string[]): Array of patterns to watch for
- `timeout_ms` (number): Maximum monitoring duration
- `buffer_lines` (number, optional): Buffer size (default: 100)

**Returns:** Task ID for monitoring the background process

#### `serial_monitor_check`
Check status of background monitoring task.

**Parameters:**
- `task_id` (string): Task ID from start_async

**Returns:** Task status, captured output, and matched patterns

#### `serial_monitor_cancel`
Cancel active background monitoring task.

**Parameters:**
- `task_id` (string): Task ID to cancel

**Returns:** Cancellation confirmation

## 💬 Usage in AI Conversations

### Example 1: Quick Device Check
```
AI: I'll check what's connected to your serial ports.
[Uses serial_monitor_list_ports]
AI: I found your Raspberry Pi Pico on COM9. Let me connect and see what it's doing.
[Uses serial_monitor_connect with port: "auto"]
[Uses serial_monitor_read with duration: 3]
AI: Your device is outputting temperature readings every 2 seconds.
```

### Example 2: Send Commands and Monitor Response
```
AI: Let me send a help command to your Pico to see available commands.
[Uses serial_monitor_send with data: "help\\n"]
[Uses serial_monitor_read with duration: 2]
AI: Here are the available commands your Pico responded with...
```

### Example 3: Background Monitoring with Alerts
```
AI: I'll monitor your device for any error messages.
[Uses serial_monitor_start_async with watch_for: ["ERROR", "FAIL"]]
AI: Background monitoring started. I'll alert you if any issues are detected.
[Later...]
[Uses serial_monitor_check with task_id]
AI: Alert! Your device reported an error: "ERROR: Sensor disconnected"
```

### Example 4: Session Analysis
```
AI: Let me check your recent serial session history.
[Uses serial_monitor_session_info]
AI: I can see you had a 45-minute session earlier today that captured 1,200 lines of data. 
The current session has been running for 12 minutes and is 234KB.
```

## 🔗 Tool Integration Features

These tools are automatically registered when the extension activates. AI agents can use them to:

1. **🔍 Debug Issues**: Connect to devices and diagnose problems automatically
2. **📊 Monitor Data**: Read sensor outputs and system status continuously  
3. **⚙️ Send Commands**: Control devices and trigger functions remotely
4. **📈 Analyze History**: Review past sessions for patterns and anomalies
5. **🤖 Automate Workflows**: Create scripted interactions with devices
6. **🚨 Alert on Patterns**: Monitor for specific conditions and alert users

## ⚙️ Configuration

The MCP tools respect all extension settings:
- Background monitoring preferences
- Session timeout and file limits  
- Default baud rates and ports
- Session directory location

Configure through: **VS Code Settings → Extensions → Serial Monitor**

## 🛠️ Technical Notes

- **Auto-detection**: When `port: "auto"` is used, the tool automatically detects Raspberry Pi Pico devices
- **Error Handling**: All tools provide detailed error messages and success indicators
- **Session Integration**: Tools work seamlessly with the extension's session management system
- **Background Safety**: Monitoring tasks have built-in timeouts and can be cancelled safely