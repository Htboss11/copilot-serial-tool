#!/usr/bin/env python3
"""
MCP Server for Copilot Serial Tool Daemon
Provides MCP protocol interface for AI agents to control the daemon
"""

import sys
import os
import json
import asyncio
from typing import Dict, Any, List, Optional

# Add daemon directory to path so we can import mcp_daemon_tools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_daemon_tools import DaemonMCPTools


class CopilotSerialToolMCPServer:
    """MCP Server that exposes daemon control tools"""
    
    def __init__(self):
        self.daemon_tools = DaemonMCPTools()
        self.protocol_version = "2024-11-05"
        self.server_name = "copilot-serial-tool-daemon"
        self.server_version = "2.0.0"
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """
        Get MCP tool definitions for the daemon
        
        Returns:
            List of tool definitions in MCP format
        """
        return [
            {
                "name": "serial_daemon_start",
                "description": "Start serial monitor daemon (idempotent - safe to call if already running). By default starts without connecting to any port. Use auto_connect=true to connect immediately. Database auto-cleanup keeps records manageable.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "auto_connect": {
                            "type": "boolean",
                            "description": "If true, automatically connect to port on startup (default: false)",
                            "default": False
                        },
                        "port": {
                            "type": "string",
                            "description": "Serial port to monitor if auto_connect=true (e.g., COM9)",
                            "default": "COM9"
                        },
                        "baudrate": {
                            "type": "integer",
                            "description": "Baud rate for serial connection if auto_connect=true",
                            "default": 115200
                        },
                        "max_records": {
                            "type": "integer",
                            "description": "Maximum database records to keep (default: 10,000). Auto-cleanup deletes oldest records.",
                            "default": 10000
                        },
                        "cleanup_interval": {
                            "type": "integer",
                            "description": "Seconds between auto-cleanup runs (default: 60)",
                            "default": 60
                        }
                    }
                }
            },
            {
                "name": "serial_daemon_stop",
                "description": "Stop serial monitor daemon gracefully (idempotent)",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "serial_daemon_status",
                "description": "Get daemon status including: running state, monitoring state, connected port, uptime, lines captured, etc.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "serial_daemon_connect",
                "description": "Connect daemon to a serial port and start monitoring. Auto-detects Raspberry Pi Pico if port not specified. Port will be exclusively held by daemon until disconnected.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "port": {
                            "type": "string",
                            "description": "Serial port to monitor (e.g., COM9). If omitted, auto-detect Raspberry Pi Pico."
                        },
                        "baudrate": {
                            "type": "integer",
                            "description": "Baud rate for serial connection",
                            "default": 115200
                        }
                    }
                }
            },
            {
                "name": "serial_daemon_disconnect",
                "description": "Disconnect daemon from serial port and stop monitoring. Releases port for other tools (PuTTY, etc.). Daemon continues running and can reconnect later.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "serial_send_data",
                "description": "Send data/command to connected serial device. Use when you need to send commands, control device, or transmit data to hardware.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "string",
                            "description": "Data string to send to device (newline will be added automatically)"
                        }
                    },
                    "required": ["data"]
                }
            },
            {
                "name": "serial_query",
                "description": "Execute SQL query on captured serial data. Query the SQLite database containing all serial port data captured by the daemon.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "sql": {
                            "type": "string",
                            "description": "SQL SELECT statement to execute"
                        },
                        "params": {
                            "type": "array",
                            "description": "Optional query parameters for prepared statement",
                            "items": {"type": "string"},
                            "default": []
                        }
                    },
                    "required": ["sql"]
                }
            },
            {
                "name": "serial_recent",
                "description": "Get recent serial data (convenience method). Returns data captured in the last N seconds.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "seconds": {
                            "type": "integer",
                            "description": "Number of seconds to look back",
                            "default": 60
                        },
                        "port": {
                            "type": "string",
                            "description": "Optional: Filter by port"
                        },
                        "session_id": {
                            "type": "string",
                            "description": "Optional: Filter by session ID"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of rows to return",
                            "default": 1000
                        }
                    }
                }
            },
            {
                "name": "serial_tail",
                "description": "Get last N lines of serial data (like tail command). Returns most recent captured lines.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "lines": {
                            "type": "integer",
                            "description": "Number of lines to return",
                            "default": 100
                        },
                        "port": {
                            "type": "string",
                            "description": "Optional: Filter by port"
                        },
                        "session_id": {
                            "type": "string",
                            "description": "Optional: Filter by session ID"
                        }
                    }
                }
            },
            {
                "name": "serial_list_ports",
                "description": "List all available serial ports with device information. Shows all COM ports, USB serial devices, and their details.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "serial_find_pico",
                "description": "Find Raspberry Pi Pico devices. Returns list of ports where Pico is detected. Useful for auto-detection.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]
    
    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle MCP tool call
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
        
        Returns:
            Tool result
        """
        try:
            # Route to appropriate daemon tool
            if tool_name == "serial_daemon_start":
                auto_connect = arguments.get("auto_connect", False)
                port = arguments.get("port", "COM9")
                baudrate = arguments.get("baudrate", 115200)
                max_records = arguments.get("max_records", 10000)
                cleanup_interval = arguments.get("cleanup_interval", 60)
                return self.daemon_tools.start_daemon(
                    auto_connect=auto_connect, 
                    port=port, 
                    baudrate=baudrate,
                    max_records=max_records,
                    cleanup_interval=cleanup_interval
                )
            
            elif tool_name == "serial_daemon_stop":
                return self.daemon_tools.stop_daemon()
            
            elif tool_name == "serial_daemon_status":
                return self.daemon_tools.get_status()
            
            elif tool_name == "serial_daemon_connect":
                port = arguments.get("port")  # Optional - will auto-detect if None
                baudrate = arguments.get("baudrate", 115200)
                return self.daemon_tools.connect_port(port, baudrate)
            
            elif tool_name == "serial_daemon_disconnect":
                return self.daemon_tools.disconnect_port()
            
            elif tool_name == "serial_send_data":
                data = arguments["data"]
                return self.daemon_tools.send_data(data)
            
            elif tool_name == "serial_query":
                sql = arguments["sql"]
                params = arguments.get("params", [])
                return self.daemon_tools.query_data(sql, params)
            
            elif tool_name == "serial_recent":
                seconds = arguments.get("seconds", 60)
                port = arguments.get("port")
                session_id = arguments.get("session_id")
                limit = arguments.get("limit", 1000)
                return self.daemon_tools.get_recent(seconds, port, session_id, limit)
            
            elif tool_name == "serial_tail":
                lines = arguments.get("lines", 100)
                port = arguments.get("port")
                session_id = arguments.get("session_id")
                return self.daemon_tools.get_tail(lines, port, session_id)
            
            elif tool_name == "serial_list_ports":
                from mcp_daemon_tools import find_serial_ports
                ports = find_serial_ports()
                return {
                    "success": True,
                    "ports": ports,
                    "count": len(ports)
                }
            
            elif tool_name == "serial_find_pico":
                from mcp_daemon_tools import find_pico_ports
                pico_ports = find_pico_ports()
                return {
                    "success": True,
                    "pico_ports": pico_ports,
                    "count": len(pico_ports),
                    "message": f"Found {len(pico_ports)} Raspberry Pi Pico device(s)"
                }
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown tool: {tool_name}"
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Error executing {tool_name}: {e}"
            }
    
    def send_response(self, response: Dict[str, Any]):
        """Send JSON-RPC response to stdout"""
        print(json.dumps(response), flush=True)
    
    async def handle_request(self, request: Dict[str, Any]):
        """Handle incoming MCP request"""
        try:
            method = request.get("method")
            request_id = request.get("id")
            
            # Handle initialize
            if method == "initialize":
                self.send_response({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": self.protocol_version,
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": {
                            "name": self.server_name,
                            "version": self.server_version
                        }
                    }
                })
            
            # Handle initialized notification (no response)
            elif method == "notifications/initialized":
                pass  # Server is now ready
            
            # Handle tools/list
            elif method == "tools/list":
                tools = self.get_tools()
                self.send_response({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"tools": tools}
                })
            
            # Handle tools/call
            elif method == "tools/call":
                params = request.get("params", {})
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                result = await self.handle_tool_call(tool_name, arguments)
                
                self.send_response({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result, indent=2)
                            }
                        ]
                    }
                })
            
            # Unknown method
            else:
                self.send_response({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                })
        
        except Exception as e:
            self.send_response({
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {e}"
                }
            })
    
    async def run(self):
        """Run MCP server (stdio interface)"""
        print("Serial Monitor Daemon MCP Server started", file=sys.stderr)
        
        buffer = ""
        
        # Read from stdin line by line
        for line in sys.stdin:
            buffer += line
            
            # Try to parse as JSON
            try:
                request = json.loads(buffer)
                buffer = ""  # Clear buffer after successful parse
                await self.handle_request(request)
            except json.JSONDecodeError:
                # Incomplete JSON, keep buffering
                continue
            except Exception as e:
                print(f"Error processing request: {e}", file=sys.stderr)
                buffer = ""  # Clear buffer on error


async def main():
    """Main entry point"""
    server = CopilotSerialToolMCPServer()
    await server.run()


if __name__ == "__main__":
    print("Copilot Serial Tool Daemon MCP Server started", file=sys.stderr)
    asyncio.run(main())
