# VS Code Serial Monitor Extension with MCP Integration

A VS Code extension that provides serial port monitoring capabilities with Model Context Protocol (MCP) tool integration, allowing AI agents like GitHub Copilot to programmatically interact with serial devices.

## Features

### 🖥️ Serial Monitor UI
- **Real-time monitoring**: Live display of serial output in a dedicated webview panel
- **Device management**: Connect/disconnect to serial ports with auto-detection for Raspberry Pi Pico devices
- **Interactive communication**: Send commands to devices via input field
- **Log management**: Clear/export functionality with syntax highlighting for errors and timestamps
- **Multi-device support**: Monitor multiple serial ports simultaneously

### 🤖 MCP Tool Integration (PRIMARY FEATURE)
The extension exposes the following tools for AI agent use:

#### `serial_monitor_start_async`
Start asynchronous monitoring of a serial port for specific patterns
- **Parameters**: `port`, `watch_for[]`, `timeout_ms`, `buffer_lines?`
- **Returns**: `{ task_id: string }`

#### `serial_monitor_check`
Check the status of a background watch task
- **Parameters**: `task_id`
- **Returns**: `{ status, output, matched_pattern?, elapsed_ms }`

#### `serial_monitor_send`
Send data to a serial device
- **Parameters**: `port`, `data`
- **Returns**: `{ success: boolean }`

#### `serial_monitor_cancel`
Cancel/close a background watch task
- **Parameters**: `task_id`
- **Returns**: `{ success: boolean }`

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

---

## Following extension guidelines

Ensure that you've read through the extensions guidelines and follow the best practices for creating your extension.

* [Extension Guidelines](https://code.visualstudio.com/api/references/extension-guidelines)

## Working with Markdown

You can author your README using Visual Studio Code. Here are some useful editor keyboard shortcuts:

* Split the editor (`Cmd+\` on macOS or `Ctrl+\` on Windows and Linux).
* Toggle preview (`Shift+Cmd+V` on macOS or `Shift+Ctrl+V` on Windows and Linux).
* Press `Ctrl+Space` (Windows, Linux, macOS) to see a list of Markdown snippets.

## For more information

* [Visual Studio Code's Markdown Support](http://code.visualstudio.com/docs/languages/markdown)
* [Markdown Syntax Reference](https://help.github.com/articles/markdown-basics/)

**Enjoy!**
