# Copilot Serial Tool

A VS Code extension that provides AI-powered serial device communication through GitHub Copilot integration. Features a Python-based daemon for real-time serial monitoring, SQLite data storage, and comprehensive MCP (Model Context Protocol) tools for AI agent control.

## 🚀 Features

- **AI-Powered Control**: GitHub Copilot can directly control serial devices
- **Bidirectional Communication**: Send commands and receive data from serial devices
- **Real-time Monitoring**: Background daemon captures serial data continuously  
- **SQLite Storage**: All serial data stored with timestamps for analysis
- **Auto-Cleanup**: Automatic database maintenance to prevent bloat
- **Zero Dependencies**: Bundled Python packages - no external installation required
- **Auto-Detection**: Automatic Raspberry Pi Pico device detection
- **Port Management**: Clean connection handling with no port locks

## 🚀 Quick Start

1. **Install the extension** from the VS Code Marketplace
2. **Daemon starts automatically** when VS Code loads
3. **Connect your device** via Copilot: *"Connect to COM9 and monitor serial data"*
4. **Query data**: *"Show me the last 100 lines of serial output"*

## 🤖 GitHub Copilot Integration (MCP)

This extension provides 12 MCP tools for GitHub Copilot to control the serial monitoring daemon:

### 💡 Natural Language Device Control
- **"Start monitoring COM9"** → Connects daemon to serial port
- **"Send 'Hello World' to the device"** → Transmits data to connected serial device
- **"Show me recent serial data"** → Queries last 60 seconds from database
- **"Disconnect the port so I can use PuTTY"** → Releases port for other tools
- **"What's the daemon status?"** → Shows running state, connected port, uptime
- **"Query all ERROR messages from the database"** → SQL query on captured data

### 🛠️ Available MCP Tools

| Tool | Description | AI Usage Example |
|------|-------------|------------------|
| `serial_daemon_start` | Start background daemon | *"Start the daemon with 10K record limit"* |
| `serial_daemon_stop` | Stop daemon gracefully | *"Stop the serial monitoring daemon"* |
| `serial_daemon_status` | Get daemon status | *"Is the daemon running?"* |
| `serial_connect_port` | Connect to serial port (auto-detect) | *"Connect to serial"* or *"Connect to COM9"* |
| `serial_disconnect_port` | Disconnect from port | *"Release COM9 for other tools"* |
| `serial_send_data` | Send data to device | *"Send 'Hello' to the device"* |
| `serial_query` | SQL query on data | *"SELECT * FROM serial_data WHERE data LIKE '%ERROR%'"* |
| `serial_recent` | Get recent data | *"Show last 60 seconds of data"* |
| `serial_tail` | Get last N lines | *"Show last 100 lines"* |
| `serial_list_ports` | List all serial ports | *"What serial ports are available?"* |
| `serial_find_pico` | Auto-detect Pico devices | *"Find my Raspberry Pi Pico"* |
| `serial_set_echo` | Enable/disable live console echo | *"Enable echo"* or *"Disable echo"* |

See [Daemon Documentation](./daemon/README.md) for detailed architecture and usage.

## 🏗️ Architecture

```
VS Code Extension
    ↓
MCP Server (Python)
    ↓
Daemon Control Tools
    ↓ JSON Commands
Serial Daemon (Background Process)
    ↓ SQLite Database
Serial Port → Hardware
```

### Key Components:
- **Serial Daemon**: Persistent background process (singleton)
- **SQLite Database**: All captured data with timestamps
- **Command Interface**: JSON file-based commands (connect/disconnect)
- **MCP Server**: Exposes daemon control to GitHub Copilot
- **File Locks**: Prevents multiple daemon instances

## ⚙️ Configuration

The daemon starts automatically with VS Code. Control it via:
- **GitHub Copilot**: Natural language commands
- **CLI**: `python daemon/mcp_daemon_tools.py [command]`

### CLI Usage:
```powershell
# Start daemon (no auto-connect)
python daemon/mcp_daemon_tools.py start --no-autoconnect

# Connect to port
python daemon/mcp_daemon_tools.py connect --port COM9 --baudrate 115200

# Check status
python daemon/mcp_daemon_tools.py status

# Disconnect (releases port)
python daemon/mcp_daemon_tools.py disconnect

# Stop daemon
python daemon/mcp_daemon_tools.py stop
```

## � Data Storage

All serial data is stored in SQLite database:
- **Location**: `~/.serial-monitor/serial_data.db`
- **Schema**: timestamp, port, data, session_id
- **Indexes**: Optimized for time-range and port queries
- **WAL Mode**: Concurrent reads during writes
- **Corruption Recovery**: Automatic integrity checks

## 📋 Requirements

- VS Code 1.74.0 or higher
- Python 3.7+ with packages:
  - `pyserial` (serial communication)
  - `sqlite3` (built-in, data storage)
- Serial device (USB, Bluetooth, or network)

## 🔧 Usage Examples

### Via GitHub Copilot (Recommended)
```
You: "Start the daemon and connect to COM9"
Copilot: [Uses serial_daemon_start and serial_daemon_connect]
Copilot: "Daemon started and connected to COM9 at 115200 baud. Monitoring active."

You: "Show me the last 50 lines"
Copilot: [Uses serial_tail with lines=50]
Copilot: [Displays captured data]

You: "Disconnect so I can use PuTTY"
Copilot: [Uses serial_daemon_disconnect]
Copilot: "Disconnected from COM9. Port is now available for other tools."
```

### Via CLI
```powershell
# Start daemon
python daemon/mcp_daemon_tools.py start --no-autoconnect

# Connect to device
python daemon/mcp_daemon_tools.py connect --port COM9 --baudrate 115200

# Query recent data
python daemon/mcp_daemon_tools.py recent --seconds 60

# Get last 100 lines
python daemon/mcp_daemon_tools.py tail --lines 100

# Disconnect port
python daemon/mcp_daemon_tools.py disconnect

# Stop daemon
python daemon/mcp_daemon_tools.py stop
```

## � Troubleshooting

- **Port Access Issues**: Use `serial_daemon_disconnect` to release port for other tools
- **Daemon Not Starting**: Check `~/.serial-monitor/daemon.log` for errors
- **Multiple Daemons**: File lock prevents this - only one daemon can run at a time
- **Database Locked**: Daemon uses WAL mode - concurrent reads are safe
- **Python Not Found**: Extension will guide you through Python installation

## 📚 Documentation

- **[Daemon Architecture](./daemon/README.md)** - Complete daemon documentation
- **[Architecture Overview](./ARCHITECTURE.md)** - System design details
- **[Stability Analysis](./STABILITY_ANALYSIS.md)** - Performance and reliability testing

## 🤝 Contributing

Contributions welcome! Please test with the daemon architecture:
1. Fork the repository
2. Test daemon functionality: `python daemon/test_mcp_server.py`
3. Submit pull request with test results

## 📄 License

MIT License - see [LICENSE](./LICENSE) for details.

## 🔗 Links

- [GitHub Repository](https://github.com/Htboss11/copilot-serial-tool)
- [VS Code Marketplace](https://marketplace.visualstudio.com/items?itemName=Htboss11.copilot-serial-tool)
- [Issues & Support](https://github.com/Htboss11/copilot-serial-tool/issues)

---

*Made with ❤️ for the maker community. Persistent serial monitoring made simple with AI assistance!* 🎉
