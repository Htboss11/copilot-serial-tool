#!/usr/bin/env node
/**
 * Standalone MCP Server for VS Code Serial Monitor
 * This server runs independently of VS Code and provides MCP tools for AI agents
 * Uses SerialManager for unified serial port management
 */

import * as path from 'path';
import { SerialManager, BufferResult } from './serialManager';

interface MCPTool {
    name: string;
    description: string;
    inputSchema: any;
}

interface MCPToolResult {
    success: boolean;
    data?: any;
    error?: string;
    message?: string;
    port?: string;
    baudRate?: number;
    buffer_seconds?: number;
    total_lines?: number;
}

class StandaloneMCPServer {
    private extensionPath: string;
    private serialManager: SerialManager;

    constructor() {
        // Find the extension path (parent directory of this script)
        this.extensionPath = path.dirname(__dirname);
        
        // Initialize SerialManager with extension path
        // Note: Running without workspace, so no session logging in standalone mode
        this.serialManager = new SerialManager(this.extensionPath);
        
        console.error('Serial Manager initialized');
        this.setupStdioInterface();
    }

    private setupStdioInterface(): void {
        // Handle MCP protocol over stdio
        let buffer = '';
        
        process.stdin.setEncoding('utf8');
        process.stdin.on('data', (chunk) => {
            buffer += chunk;
            const lines = buffer.split('\n');
            buffer = lines.pop() || ''; // Keep incomplete line in buffer
            
            for (const line of lines) {
                const trimmed = line.trim();
                if (trimmed) {
                    this.handleMCPRequest(trimmed);
                }
            }
        });

        // Keep the process alive
        process.stdin.on('end', () => {
            console.error('stdin closed, exiting');
            process.exit(0);
        });

        // Handle errors
        process.on('uncaughtException', (error) => {
            console.error('Uncaught exception:', error);
        });
    }    private async handleMCPRequest(request: string): Promise<void> {
        try {
            const req = JSON.parse(request);
            
            // Handle initialize request
            if (req.method === 'initialize') {
                this.sendMCPResponse({
                    jsonrpc: '2.0',
                    id: req.id,
                    result: {
                        protocolVersion: '2024-11-05',
                        capabilities: {
                            tools: {}
                        },
                        serverInfo: {
                            name: 'serial-monitor-mcp',
                            version: '1.0.0'
                        }
                    }
                });
            }
            // Handle initialized notification (no response needed)
            else if (req.method === 'notifications/initialized') {
                // Server is now ready
            }
            // Handle tools/list request
            else if (req.method === 'tools/list') {
                const tools = this.getTools();
                this.sendMCPResponse({
                    jsonrpc: '2.0',
                    id: req.id,
                    result: { tools }
                });
            }
            // Handle tools/call request
            else if (req.method === 'tools/call') {
                const result = await this.handleToolCall(req.params.name, req.params.arguments || {});
                this.sendMCPResponse({
                    jsonrpc: '2.0',
                    id: req.id,
                    result: { content: [{ type: 'text', text: JSON.stringify(result) }] }
                });
            }
            // Unknown method
            else {
                this.sendMCPResponse({
                    jsonrpc: '2.0',
                    id: req.id,
                    error: { code: -32601, message: `Method not found: ${req.method}` }
                });
            }
        } catch (error) {
            console.error('Error handling MCP request:', error);
            this.sendMCPResponse({
                jsonrpc: '2.0',
                id: null,
                error: { code: -32700, message: 'Parse error', data: String(error) }
            });
        }
    }

    private sendMCPResponse(response: any): void {
        process.stdout.write(JSON.stringify(response) + '\n');
    }

    private getTools(): MCPTool[] {
        return [
            {
                name: 'serial_monitor_list_ports',
                description: 'Lists all available serial ports on the system with detailed device information including VID/PID, manufacturer, and description. Use this to discover connected devices or troubleshoot connection issues.',
                inputSchema: {
                    type: 'object',
                    properties: {},
                    required: []
                }
            },
            {
                name: 'serial_monitor_connect',
                description: 'Establishes a connection to a serial device. Must be called before sending or reading data. The connection persists until explicitly disconnected. Automatically detects Raspberry Pi Pico devices.',
                inputSchema: {
                    type: 'object',
                    properties: {
                        port: { 
                            type: 'string', 
                            description: 'Serial port path (e.g., COM9 on Windows, /dev/ttyUSB0 on Linux). Required.' 
                        },
                        baudRate: { 
                            type: 'number', 
                            description: 'Communication speed in bits per second. Common values: 9600, 115200. Default: 115200' 
                        }
                    },
                    required: ['port']
                }
            },
            {
                name: 'serial_monitor_send',
                description: 'Sends data to a connected serial device. The device must be connected first using serial_monitor_connect. Data is sent as UTF-8 text.',
                inputSchema: {
                    type: 'object',
                    properties: {
                        port: { 
                            type: 'string', 
                            description: 'Serial port path where the device is connected. Required.' 
                        },
                        data: { 
                            type: 'string', 
                            description: 'Text data to send to the device. Required.' 
                        }
                    },
                    required: ['port', 'data']
                }
            },
            {
                name: 'serial_monitor_read',
                description: 'Reads data from a connected serial device for a specified duration. The device must be connected first using serial_monitor_connect. Returns all lines received during the read period with timestamps.',
                inputSchema: {
                    type: 'object',
                    properties: {
                        port: { 
                            type: 'string', 
                            description: 'Serial port path where the device is connected. Required.' 
                        },
                        duration: { 
                            type: 'number', 
                            description: 'How many seconds to read data. Default: 5 seconds. Increase for slow devices or large data transfers.' 
                        }
                    },
                    required: ['port']
                }
            },
            {
                name: 'serial_monitor_get_buffer',
                description: 'Retrieves buffered data from a connected serial device. The buffer automatically stores the last 10 minutes (600 seconds) of data with timestamps and connection state markers (CONNECTION ESTABLISHED, CONNECTION LOST, CONNECTION RESTORED, DISCONNECTED BY USER). Use this to review historical data or check connection status. Optionally filter to last N seconds.',
                inputSchema: {
                    type: 'object',
                    properties: {
                        port: { 
                            type: 'string', 
                            description: 'Serial port path where the device is connected. Required.' 
                        },
                        seconds: { 
                            type: 'number', 
                            description: 'Optional: Return only data from the last N seconds. Omit to get all buffered data (up to 10 minutes).' 
                        }
                    },
                    required: ['port']
                }
            }
        ];
    }

    private async handleToolCall(toolName: string, params: any): Promise<MCPToolResult> {
        try {
            switch (toolName) {
                case 'serial_monitor_list_ports':
                    return await this.listPorts();
                case 'serial_monitor_connect':
                    return await this.connectToPort(params.port, params.baudRate || 115200);
                case 'serial_monitor_send':
                    return await this.sendData(params.port, params.data);
                case 'serial_monitor_read':
                    return await this.readData(params.port, params.duration || 5);
                case 'serial_monitor_get_buffer':
                    return await this.getBuffer(params.port, params.seconds);
                default:
                    return { success: false, error: `Unknown tool: ${toolName}` };
            }
        } catch (error) {
            return { success: false, error: String(error) };
        }
    }

    private async listPorts(): Promise<MCPToolResult> {
        try {
            const ports = await this.serialManager.listPorts();
            return { success: true, data: ports };
        } catch (error) {
            return { success: false, error: `Failed to list ports: ${error}` };
        }
    }

    private async connectToPort(port: string, baudRate: number): Promise<MCPToolResult> {
        try {
            const success = await this.serialManager.connect(port, baudRate);
            if (success) {
                return {
                    success: true,
                    message: `Connected to ${port} at ${baudRate} baud with auto-reconnect and logging`,
                    port,
                    baudRate
                };
            } else {
                return { success: false, error: `Failed to connect to ${port}` };
            }
        } catch (error) {
            return { success: false, error: `Failed to connect to ${port}: ${error}` };
        }
    }

    private async sendData(port: string, data: string): Promise<MCPToolResult> {
        try {
            const success = await this.serialManager.send(port, data);
            if (success) {
                return { success: true, message: `Sent ${data.length} bytes to ${port}` };
            } else {
                return { success: false, error: `Failed to send data to ${port}` };
            }
        } catch (error) {
            return { success: false, error: `Failed to send data to ${port}: ${error}` };
        }
    }

    private async readData(port: string, duration: number): Promise<MCPToolResult> {
        try {
            const result = await this.serialManager.read(port, duration);
            return result;
        } catch (error) {
            return { success: false, error: `Failed to read from ${port}: ${error}` };
        }
    }

    private async getBuffer(port: string, seconds?: number): Promise<MCPToolResult> {
        try {
            const result = await this.serialManager.getBuffer(port, seconds);
            return result;
        } catch (error) {
            return { success: false, error: `Failed to get buffer from ${port}: ${error}` };
        }
    }
}

// Start the MCP server
new StandaloneMCPServer();