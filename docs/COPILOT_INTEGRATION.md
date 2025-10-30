# GitHub Copilot Integration

This extension integrates with GitHub Copilot through VS Code's Language Model Tools API, providing AI-powered serial device interaction capabilities.

## Available Tools for GitHub Copilot

The extension registers 8 tools that GitHub Copilot can use to interact with serial devices:

### 1. `serial_monitor_connect`
**Purpose**: Connect to a serial port with auto-detection for Raspberry Pi Pico devices

**Parameters**:
- `port` (string, required): Serial port path (e.g., 'COM9') or 'auto' to detect Pico
- `baud_rate` (number, optional): Baud rate (default: 115200)

**Usage**: 
- "Connect to my Arduino on COM3"
- "Auto-detect and connect to my Pico"
- "Connect to /dev/ttyUSB0 at 9600 baud"

### 2. `serial_monitor_send`
**Purpose**: Send data to connected serial device

**Parameters**:
- `port` (string, required): Serial port path or 'auto'
- `data` (string, required): Data to send to device

**Usage**:
- "Send 'hello world' to my device"
- "Turn on LED by sending '1'"
- "Send the command 'reset' to COM3"

### 3. `serial_monitor_read`
**Purpose**: Read data from serial port for specified duration

**Parameters**:
- `port` (string, required): Serial port path or 'auto'
- `duration` (number, required): Duration in seconds to read
- `timeout` (number, optional): Timeout in milliseconds (default: 1000)

**Usage**:
- "Read data from my device for 5 seconds"
- "Listen to COM3 for 10 seconds"
- "Capture output for 3 seconds with 2000ms timeout"

### 4. `serial_monitor_list_ports`
**Purpose**: List all available serial ports

**Parameters**: None

**Usage**:
- "What serial ports are available?"
- "List all connected devices"
- "Show me the available COM ports"

### 5. `serial_monitor_session_info`
**Purpose**: Get information about current and historical sessions

**Parameters**: None

**Usage**:
- "Show me my session history"
- "What devices have I connected to recently?"
- "Display current monitoring status"

### 6. `serial_monitor_start_watch`
**Purpose**: Start background monitoring with pattern matching

**Parameters**:
- `port` (string, required): Serial port path or 'auto'
- `watch_for` (array of strings, required): Array of patterns to watch for
- `timeout_ms` (number, required): Maximum monitoring duration in milliseconds
- `buffer_lines` (number, optional): Buffer size (default: 100)

**Usage**:
- "Watch for 'ERROR' or 'EXCEPTION' messages on COM3 for 30 seconds"
- "Monitor my device for temperature readings over 5 minutes"
- "Start watching for boot messages on my Pico"

### 7. `serial_monitor_check_watch`
**Purpose**: Check status of background monitoring task

**Parameters**:
- `task_id` (string, required): Task ID from start_watch

**Usage**:
- "Check the status of watch task abc123"
- "Has my monitoring task found any patterns?"
- "Show me the results of background monitoring"

### 8. `serial_monitor_stop_watch`
**Purpose**: Stop background monitoring task

**Parameters**:
- `task_id` (string, required): Task ID to stop

**Usage**:
- "Stop the monitoring task abc123"
- "Cancel background watching"
- "End the pattern monitoring"

## Example Copilot Conversations

### Basic Device Interaction
```
User: "I want to connect to my Arduino and send some commands"

Copilot: I'll help you connect to your Arduino and send commands. Let me first see what ports are available:

[Uses serial_monitor_list_ports]

I can see several ports available. Let me connect to COM3 which looks like your Arduino:

[Uses serial_monitor_connect with port: "COM3"]

Great! Now connected. What command would you like to send?

User: "Send 'LED_ON' to turn on the LED"

Copilot: [Uses serial_monitor_send with port: "COM3", data: "LED_ON"]

Command sent successfully! Your LED should now be on.
```

### Advanced Monitoring
```
User: "I want to monitor my IoT device for any error messages while I test it"

Copilot: I'll set up background monitoring to watch for error patterns. Let me start monitoring:

[Uses serial_monitor_start_watch with port: "auto", watch_for: ["ERROR", "FAIL", "EXCEPTION"], timeout_ms: 300000]

I've started monitoring your device for error messages (ERROR, FAIL, EXCEPTION) for the next 5 minutes. The task ID is xyz789.

You can continue with your testing, and I'll check for any errors periodically. Would you like me to check the monitoring status now?

User: "Yes, check if any errors were found"

Copilot: [Uses serial_monitor_check_watch with task_id: "xyz789"]

No error patterns detected so far. Your device appears to be running normally!
```

## Integration Architecture

The extension uses a dual integration approach:

1. **Language Model Tools API** (Primary): Modern VS Code API that GitHub Copilot uses directly
2. **Model Context Protocol (MCP)** (Legacy): Fallback for other AI tools

This ensures maximum compatibility and follows Microsoft's recommended practices for AI tool integration.

## Tool Discovery

GitHub Copilot automatically discovers these tools through the `languageModelTools` contribution point in `package.json`. Each tool includes:

- **Display Name**: Human-readable name for the tool
- **Model Description**: Detailed description for AI understanding
- **Input Schema**: JSON Schema defining parameters
- **Tags**: Semantic tags for tool categorization

## Error Handling

All tools provide robust error handling:
- Clear error messages for common issues
- Graceful fallbacks for connection problems
- Detailed status information for debugging

## Performance Considerations

- Tools are registered lazily during extension activation
- Background monitoring uses efficient event-based patterns
- Session management provides historical context without memory leaks
- Auto-detection minimizes user configuration requirements

## Troubleshooting

If GitHub Copilot cannot see the tools:
1. Ensure VS Code is up to date (Language Model Tools requires recent versions)
2. Check that the extension is activated
3. Verify GitHub Copilot extension is installed and signed in
4. Look for registration messages in the extension host output

For debugging tool behavior:
1. Check the Output panel for "Serial Monitor" logs
2. Use the session info tool to see connection history
3. Verify device permissions and drivers are correct