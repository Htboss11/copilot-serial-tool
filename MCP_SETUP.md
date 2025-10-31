# MCP Server Setup for VS Code Serial Monitor

This guide explains how to configure the Serial Monitor MCP server so AI agents like GitHub Copilot can discover and use the serial communication tools.

## What is MCP?

Model Context Protocol (MCP) allows AI agents to discover and interact with external tools. By registering the Serial Monitor as an MCP server, AI agents can programmatically:

- List available serial ports
- Connect to devices
- Send and receive data
- Start background monitoring
- Manage async watch tasks

## Installation Steps

### 1. Locate Your MCP Configuration

The MCP configuration location depends on your system:

**Windows:**
- VS Code: `%APPDATA%\Code\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json`
- Claude Desktop: `%APPDATA%\Claude\claude_desktop_config.json`

**macOS:**
- VS Code: `~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`
- Claude Desktop: `~/Library/Application Support/Claude/claude_desktop_config.json`

**Linux:**
- VS Code: `~/.config/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`
- Claude Desktop: `~/.config/claude/claude_desktop_config.json`

### 2. Add Serial Monitor Server

Add this configuration to your MCP settings file:

```json
{
  "mcpServers": {
    "serial-monitor": {
      "command": "node",
      "args": ["PATH_TO_EXTENSION/dist/mcp-server-standalone.js"],
      "env": {}
    }
  }
}
```

**Replace `PATH_TO_EXTENSION` with the actual path to your extension installation:**

For VS Code extensions, this is typically:
- Windows: `%USERPROFILE%\.vscode\extensions\htboss11.serial-monitor-1.0.0`
- macOS: `~/.vscode/extensions/htboss11.serial-monitor-1.0.0`
- Linux: `~/.vscode/extensions/htboss11.serial-monitor-1.0.0`

### 3. Example Complete Configuration

```json
{
  "mcpServers": {
    "serial-monitor": {
      "command": "node",
      "args": ["C:\\Users\\YourName\\.vscode\\extensions\\htboss11.serial-monitor-1.0.0\\dist\\mcp-server-standalone.js"],
      "env": {}
    }
  }
}
```

### 4. Restart Your MCP Client

After adding the configuration:
- Restart VS Code (if using Claude Dev or similar MCP client)
- Restart Claude Desktop (if using Claude Desktop)

## Available Tools

Once configured, AI agents will have access to these tools:

- **`serial_monitor_list_ports`** - List all available serial ports
- **`serial_monitor_connect`** - Connect to a specific port
- **`serial_monitor_send`** - Send data to connected device
- **`serial_monitor_read`** - Read data from device
- **`serial_monitor_start_async`** - Start background monitoring with pattern matching
- **`serial_monitor_check`** - Check status of background tasks
- **`serial_monitor_cancel`** - Cancel background tasks
- **`serial_monitor_session_info`** - Get session information

## Verification

To verify the setup works:

1. Ask your AI agent: "Can you list available serial ports?"
2. The agent should use the `serial_monitor_list_ports` tool
3. You should see the actual ports on your system

## Troubleshooting

### MCP Server Not Found
- Verify the path to `mcp-server-standalone.js` is correct
- Ensure Node.js is installed and in your PATH
- Check the MCP configuration file syntax is valid JSON

### Permission Errors
- Ensure the extension files have proper read permissions
- On Linux/macOS, you may need to make the script executable

### Dependencies Missing
- The MCP server automatically checks for Python and pyserial
- If missing, it will return appropriate error messages
- Install using: `pip install pyserial`

## Manual Testing

You can test the MCP server directly:

```bash
cd path/to/extension
node dist/mcp-server-standalone.js
```

Then send MCP protocol messages via stdin to test functionality.