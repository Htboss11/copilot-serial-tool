# Changelog

All notable changes to the "Serial Monitor with AI Integration" extension will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-10-30

### 🎉 Initial Release

#### Added
- **Real-time Serial Monitoring**: Connect to and monitor serial devices with responsive UI
- **AI Agent Integration**: Complete MCP (Model Context Protocol) implementation for GitHub Copilot
- **Auto-detection**: Automatic discovery of Raspberry Pi Pico and compatible devices  
- **Background Monitoring**: Continuous logging with configurable session management
- **Session File Rotation**: Automatic file management with size and count limits (1-100 files, 1-100MB each)
- **Python Backend**: Reliable cross-platform serial communication using pyserial
- **8 MCP Tools** for AI integration:
  - `serial_monitor_connect` - Connect to serial ports with auto-detection
  - `serial_monitor_send` - Send data to connected devices
  - `serial_monitor_read` - Read device output for specified duration
  - `serial_monitor_list_ports` - List all available serial ports
  - `serial_monitor_session_info` - Get session information and statistics
  - `serial_monitor_start_async` - Start background monitoring with pattern matching
  - `serial_monitor_check` - Check status of background monitoring tasks
  - `serial_monitor_cancel` - Cancel active background monitoring
- **Configurable Settings**: 6 VS Code settings for customization
- **Session Management**: Timestamped session files with device information headers
- **Professional Documentation**: Comprehensive guides and examples

#### Technical Features
- Cross-platform compatibility (Windows, macOS, Linux)
- TypeScript frontend with modern VS Code extension architecture
- Python subprocess backend for reliable serial communication
- WebView UI for real-time display and interaction
- Error handling and reconnection logic
- Marketplace-ready packaging with MIT license

#### AI Integration Highlights
- Natural language device control through Copilot
- Automatic pattern monitoring and alerting
- Session analysis and historical data review
- Scriptable device interactions
- Seamless integration with VS Code workflows

---

## Future Releases

### Planned Features
- [ ] Support for additional device types and protocols
- [ ] Advanced pattern matching with regex support
- [ ] Data visualization and plotting capabilities
- [ ] Export functionality for session data
- [ ] Integration with other VS Code extensions
- [ ] Custom device profiles and configurations

---

*For detailed usage instructions, see [README.md](./README.md)*  
*For AI tool documentation, see [MCP-TOOLS-GUIDE.md](./MCP-TOOLS-GUIDE.md)*