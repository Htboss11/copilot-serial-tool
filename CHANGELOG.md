# Change Log

All notable changes to the "Copilot Serial Tool" extension will be documented in this file.

## [1.5.0] - 2024-11-09

### Added
- **Auto-Connect Feature**: Automatically detects and connects to Raspberry Pi Pico devices without specifying port
- **Live Echo Control**: New `serial_set_echo` MCP tool to enable/disable real-time console output
- **Enhanced Port Discovery**: Improved Pico detection with VID/PID validation
- **Two-Stage Reconnection**: Intelligent retry strategy (rapid retry → slow retry → timeout)
- **Database Auto-Cleanup**: Automatic maintenance to keep database size manageable
- **Smart Error Messages**: Clear guidance when multiple Picos detected or none found
- **Complete Self-Containment**: All dependencies (pyserial, psutil, mcp) vendored - zero user setup required

### Changed
- Updated MCP tool count from 11 to 12 tools
- Renamed `serial_daemon_connect` → `serial_connect_port` (supports auto-detection)
- Renamed `serial_daemon_disconnect` → `serial_disconnect_port`
- Improved error handling for Unicode characters in console output
- Enhanced status reporting with session tracking and uptime

### Fixed
- Unicode encoding issues in Windows console output
- Port release behavior for better compatibility with other tools
- Database connection handling in multi-access scenarios

## [1.4.1] - 2024-11-08

### Fixed
- Daemon startup reliability improvements
- MCP server connection stability
- Port detection on Windows systems

## [1.4.0] - 2024-11-07

### Added
- Initial MCP (Model Context Protocol) integration
- GitHub Copilot natural language control
- Background daemon for persistent monitoring
- SQLite database for serial data storage
- 11 MCP tools for AI agent control

### Features
- Real-time serial monitoring
- Bidirectional communication
- Port management with clean disconnect
- Time-based and line-based data queries
- SQL query support on captured data
- Automatic Raspberry Pi Pico detection

## [1.0.0] - 2024-11-01

### Added
- Initial release
- Basic serial port monitoring
- Python-based backend
- VS Code extension framework
- Serial port listing and connection
- Data capture to database

---

For more details, see the [GitHub repository](https://github.com/Htboss11/copilot-serial-tool).
