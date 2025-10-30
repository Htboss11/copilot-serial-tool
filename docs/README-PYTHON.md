# VS Code Serial Monitor Extension with Python Backend

This VS Code extension provides serial port monitoring capabilities using a Python backend to avoid native module compilation issues.

## Setup Requirements

1. **Python with pyserial**: The extension uses a Python script for serial communication
   ```bash
   pip install pyserial
   ```

2. **VS Code Engine**: Requires VS Code 1.74.0 or higher

## Architecture

- **Extension (TypeScript)**: Handles VS Code integration, UI, and command registration
- **Python Backend**: Manages actual serial communication using pyserial
- **Output Channels**: Serial data appears in VS Code Output panel
- **Webview UI**: Provides connection controls and status

## Key Files

- `src/extension.ts` - Main extension entry point
- `src/serialManager.ts` - Python process manager for serial communication
- `src/webview/SerialPanel.ts` - Webview UI for serial monitoring
- `python/serial_monitor.py` - Python script for serial operations
- `python/requirements.txt` - Python dependencies

## Usage

1. Open Command Palette (Ctrl+Shift+P)
2. Run "Open Serial Monitor"
3. Extension auto-detects Raspberry Pi Pico on COM9
4. Serial data appears in Output panel: "Serial Monitor - COM9"

## Features

- Auto-detect Raspberry Pi Pico devices
- Real-time serial monitoring via Output channels
- Send data to connected devices
- Auto-reconnect functionality
- Background Python processes for non-blocking operation

## Troubleshooting

- **Python not found**: Ensure Python is in PATH
- **Permission denied**: Run VS Code as administrator if needed
- **pyserial missing**: Install with `pip install pyserial`
- **Port access issues**: Close other serial monitor applications

## Development Notes

This approach was chosen to avoid Electron ABI compatibility issues with native Node.js modules like serialport. The Python backend provides reliable cross-platform serial communication.