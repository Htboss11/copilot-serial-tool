# VS Code Serial Monitor with GitHub Copilot Integration

A powerful VS Code extension that provides serial port monitoring with seamless GitHub Copilot integration using VS Code's modern Language Model Tools API.

## ✨ Features

- **Real-time Serial Monitoring**: Connect to and monitor serial devices with a clean, responsive interface
- **GitHub Copilot Integration**: Native Language Model Tools enable natural language device control
- **Auto-detection**: Automatically finds Raspberry Pi Pico and other common devices
- **Background Monitoring**: Continuous logging with pattern matching and alerts
- **Session Management**: Automatic file management with size and count limits
- **Advanced Watch Tasks**: Background monitoring with timeout and pattern detection

## 🚀 Quick Start

1. **Install the extension** from the VS Code Marketplace
2. **Connect your device** (e.g., Raspberry Pi Pico on COM9)
3. **Open Serial Monitor**: `Ctrl+Shift+P` → "Open Serial Monitor"
4. **Chat with Copilot**: Let GitHub Copilot handle device interaction naturally

## 🤖 GitHub Copilot Integration

This extension registers 8 tools with GitHub Copilot using VS Code's Language Model Tools API:

### 💡 Natural Language Device Control
- **"Connect to my Pico and read sensor data"** → Auto-detects, connects, and captures output
- **"Send 'LED_ON' to turn on the LED"** → Sends command to connected device  
- **"Monitor for error messages for 5 minutes"** → Starts background pattern monitoring
- **"What serial ports are available?"** → Lists all detected serial devices
- **"Show my session history"** → Displays connection history and statistics

### 🛠️ Available Copilot Tools

| Tool | Description | AI Usage Example |
|------|-------------|------------------|
| `serial_monitor_connect` | Connect to serial port | *"Connect to COM9 at 115200 baud"* |
| `serial_monitor_send` | Send data to device | *"Send 'reset' command to my device"* |
| `serial_monitor_read` | Read device output | *"Capture output for 10 seconds"* |
| `serial_monitor_list_ports` | List available ports | *"What devices are connected?"* |
| `serial_monitor_session_info` | Get session details | *"Show my connection history"* |
| `serial_monitor_start_watch` | Start background monitoring | *"Watch for 'ERROR' or 'FAIL' messages"* |
| `serial_monitor_check_watch` | Check monitoring status | *"Has my monitoring found any issues?"* |
| `serial_monitor_stop_watch` | Stop background monitoring | *"Cancel the background monitoring"* |

See [GitHub Copilot Integration Guide](./docs/COPILOT_INTEGRATION.md) for detailed integration documentation.

## ⚙️ Configuration

Configure the extension through VS Code Settings → Extensions → Serial Monitor:

- **Background Monitoring**: Enable automatic device monitoring
- **Session Timeout**: Set maximum session duration (60-86400 seconds)
- **File Rotation**: Configure session file limits (1-100 files, 1-100MB each)
- **Default Settings**: Set preferred baud rates and connection parameters

## 📁 Session Management

- **Automatic File Rotation**: Sessions are saved with timestamps and rotated based on your limits
- **Session Headers**: Each file includes device info, timestamps, and configuration
- **Background Logging**: Continuous monitoring even when the panel is closed
- **File Organization**: Clean, organized session files for easy analysis

## 🛠️ Technical Details

- **Cross-platform**: Works on Windows, macOS, and Linux
- **Python Backend**: Reliable serial communication using pyserial
- **TypeScript Frontend**: Modern VS Code extension with webview UI
- **MCP Integration**: Standard Model Context Protocol for AI tool integration

## 📋 Requirements

- VS Code 1.74.0 or higher
- Python 3.7+ (automatically detected)
- Serial device (USB, Bluetooth, or network)

## 🔧 Usage Examples

### Manual Operation
1. Open Command Palette (`Ctrl+Shift+P`)
2. Run "Open Serial Monitor"
3. Select your port or use auto-detection
4. Start monitoring or send commands

### AI-Assisted Operation
```
You: "Check what's happening on my Pico"
Copilot: [Uses serial_monitor_connect with auto-detection]
Copilot: [Uses serial_monitor_read for 3 seconds]
Copilot: "Your Pico is running the temperature sensor script and reporting 23.5°C"

You: "Send a reset command"
Copilot: [Uses serial_monitor_send with "reset\n"]
Copilot: "Reset command sent successfully"
```

## 🐛 Troubleshooting

- **Port Access Issues**: Ensure no other applications are using the serial port
- **Python Not Found**: Extension will guide you through Python installation
- **Device Not Detected**: Check USB connections and device drivers
- **Permission Errors**: Run VS Code as administrator if needed (Windows)

## 📚 Resources

- [MCP Tools Guide](./MCP-TOOLS-GUIDE.md) - Detailed AI tool documentation
- [Session Management](./docs/sessions.md) - Session file format and management
- [Troubleshooting Guide](./docs/troubleshooting.md) - Common issues and solutions

## 🤝 Contributing

Contributions welcome! Please see [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

## 📄 License

MIT License - see [LICENSE](./LICENSE) for details.

## 🔗 Links

- [GitHub Repository](https://github.com/Htboss11/copilot-serial-tool)
- [VS Code Marketplace](https://marketplace.visualstudio.com/items?itemName=Htboss11.copilot-serial-tool)
- [Issues & Support](https://github.com/Htboss11/copilot-serial-tool/issues)

---

*Made with ❤️ for the maker community. Happy monitoring!*

### ⚡ Background Task Manager
- Run serial watches asynchronously without blocking the UI
- Support multiple simultaneous watches on different ports
- Circular buffer for efficient output storage
- Pattern matching with regex support
- Automatic timeout handling

## Requirements

- VS Code 1.105.0 or higher
- Node.js (for serial communication)
- Serial devices (tested with Raspberry Pi Pico)

## Installation & Usage

### Development Setup
1. Clone this repository
2. Run `npm install` to install dependencies
3. Press `F5` to launch the extension in a new Extension Development Host window

### Commands
- **Serial Monitor: Open Serial Monitor** - Opens the serial monitoring webview
- **Serial Monitor: List Serial Ports** - Shows available serial ports in a quick pick
- **Serial Monitor: Detect Raspberry Pi Pico** - Auto-detects connected Pico devices

## Extension Settings

This extension contributes the following settings:

* `serialMonitor.defaultBaudRate`: Default baud rate for serial connections (default: 115200)
* `serialMonitor.bufferLines`: Number of lines to keep in buffer (default: 1000)
* `serialMonitor.autoDetectPico`: Automatically detect Raspberry Pi Pico devices (default: true)
* `serialMonitor.watchTimeout`: Default timeout for watch operations in milliseconds (default: 60000)

## AI Agent Integration Example

```typescript
// AI Agent workflow example
const taskId = await vscode.commands.executeCommand('serial-monitor.mcp.serial_monitor_start_async', {
    port: "auto",  // Auto-detect Pico
    watch_for: ["Scan complete", "ERROR"],
    timeout_ms: 30000,
    buffer_lines: 100
});

// Poll for results
const status = await vscode.commands.executeCommand('serial-monitor.mcp.serial_monitor_check', {
    task_id: taskId.data.task_id
});

// Send command
await vscode.commands.executeCommand('serial-monitor.mcp.serial_monitor_send', {
    port: "COM9",
    data: "scan\n"
});
```

## Architecture

The extension is built with:
- **TypeScript** for robust type safety
- **SerialPort** library for serial communication
- **MCP Protocol** for AI agent integration
- **Webview API** for the user interface
- **Async Task Management** for background operations

## Testing

1. Connect a Raspberry Pi Pico or other serial device
2. Launch the extension with `F5`
3. Use the command palette: "Serial Monitor: Open Serial Monitor"
4. Test auto-detection and manual connection
5. Send commands and monitor output
6. Test MCP tools via AI agent integration

## Known Issues

- Serial port access may require appropriate permissions on some systems
- Hot-plugging of devices may require manual refresh of port list

## Release Notes

### 0.0.1
- Initial release with core serial monitoring functionality
- MCP tool integration for AI agents
- Webview UI for real-time monitoring
- Auto-detection for Raspberry Pi Pico devices
- Async watch management with pattern matching

---

**Enjoy using the Serial Monitor extension with AI agent integration!**

## 📚 Documentation

- **[GitHub Copilot Integration Guide](./docs/COPILOT_INTEGRATION.md)** - Detailed guide for AI tool integration
- **[MCP Tools Reference](./docs/MCP-TOOLS-GUIDE.md)** - Complete tool documentation for developers
- **[Python Backend Guide](./docs/README-PYTHON.md)** - Technical details about the Python serial backend

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Links

- **[GitHub Repository](https://github.com/Htboss11/copilot-serial-tool)**
- **[VS Code Marketplace](https://marketplace.visualstudio.com/items?itemName=Htboss11.serial-monitor)**
- **[Issue Tracker](https://github.com/Htboss11/copilot-serial-tool/issues)**

---

**Enjoy seamless serial device interaction with AI assistance!** 🎉
