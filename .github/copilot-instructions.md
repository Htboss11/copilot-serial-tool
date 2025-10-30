# VS Code Serial Monitor Extension with MCP Integration

This VS Code extension provides serial port monitoring capabilities with Model Context Protocol (MCP) tool integration, allowing AI agents like GitHub Copilot to programmatically interact with serial devices.

## Project Structure
- TypeScript VS Code extension
- Serial communication using `serialport` package
- MCP server implementation for AI agent integration
- Webview UI for real-time serial monitoring
- Async watch management for background tasks

## Key Features
- Real-time serial port monitoring
- Auto-detect Raspberry Pi Pico devices
- MCP tools for AI agent interaction
- Background async watch tasks
- Pattern matching and timeout handling

## Development Guidelines
- Follow VS Code extension best practices
- Implement proper error handling for serial communication
- Use async/await patterns for non-blocking operations
- Maintain clean separation between UI, business logic, and MCP server
- Test with real hardware when possible