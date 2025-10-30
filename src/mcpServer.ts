import { SerialManager } from './serialManager';
import { WatchManager, WatchConfig } from './watchManager';

export interface MCPTool {
    name: string;
    description: string;
    inputSchema: any;
}

export interface MCPToolResult {
    success: boolean;
    data?: any;
    error?: string;
}

export class MCPServer {
    private serialManager: SerialManager;
    private watchManager: WatchManager;

    constructor(serialManager: SerialManager, watchManager: WatchManager) {
        this.serialManager = serialManager;
        this.watchManager = watchManager;
        this.announceCapabilities();
    }

    /**
     * Announce MCP capabilities to AI agents like GitHub Copilot
     * This helps AI agents discover and understand available serial tools
     */
    private announceCapabilities(): void {
        // Register capability announcement with VS Code
        console.log('Serial Monitor MCP Tools Available:');
        console.log('- serial_monitor_start_async: Start background monitoring with pattern matching');
        console.log('- serial_monitor_check: Check status of background watch tasks');
        console.log('- serial_monitor_send: Send data to connected devices');
        console.log('- serial_monitor_cancel: Cancel background watch tasks');
        console.log('- serial_monitor_connect: Connect to serial devices');
        console.log('- serial_monitor_read: Read data from devices');
        console.log('- serial_monitor_list_ports: List available ports');
        console.log('- serial_monitor_session_info: Get session information');
    }

    getTools(): MCPTool[] {
        return [
            {
                name: 'serial_monitor_start_async',
                description: 'Start async monitoring of serial port for specific patterns',
                inputSchema: {
                    type: 'object',
                    properties: {
                        port: {
                            type: 'string',
                            description: 'Serial port path (e.g., "COM9") or "auto" to detect Pico'
                        },
                        watch_for: {
                            type: 'array',
                            items: { type: 'string' },
                            description: 'Array of patterns to watch for (supports regex)'
                        },
                        timeout_ms: {
                            type: 'number',
                            description: 'Maximum watch duration in milliseconds'
                        },
                        buffer_lines: {
                            type: 'number',
                            description: 'Number of lines to keep in buffer (default: 100)',
                            default: 100
                        }
                    },
                    required: ['port', 'watch_for', 'timeout_ms']
                }
            },
            {
                name: 'serial_monitor_check',
                description: 'Check status of background watch task',
                inputSchema: {
                    type: 'object',
                    properties: {
                        task_id: {
                            type: 'string',
                            description: 'Task ID returned from start_async'
                        }
                    },
                    required: ['task_id']
                }
            },
            {
                name: 'serial_monitor_send',
                description: 'Send data to serial device',
                inputSchema: {
                    type: 'object',
                    properties: {
                        port: {
                            type: 'string',
                            description: 'Serial port path (e.g., "COM9")'
                        },
                        data: {
                            type: 'string',
                            description: 'Data to send to device'
                        }
                    },
                    required: ['port', 'data']
                }
            },
            {
                name: 'serial_monitor_cancel',
                description: 'Cancel/close background watch task',
                inputSchema: {
                    type: 'object',
                    properties: {
                        task_id: {
                            type: 'string',
                            description: 'Task ID to cancel'
                        }
                    },
                    required: ['task_id']
                }
            },
            {
                name: 'serial_monitor_connect',
                description: 'Connect to a serial port',
                inputSchema: {
                    type: 'object',
                    properties: {
                        port: {
                            type: 'string',
                            description: 'Serial port path (e.g., "COM9") or "auto" to detect Pico'
                        },
                        baud_rate: {
                            type: 'number',
                            description: 'Baud rate (default: 115200)',
                            default: 115200
                        }
                    },
                    required: ['port']
                }
            },
            {
                name: 'serial_monitor_read',
                description: 'Read data from serial port for specified duration',
                inputSchema: {
                    type: 'object',
                    properties: {
                        port: {
                            type: 'string',
                            description: 'Serial port path or "auto"'
                        },
                        duration: {
                            type: 'number',
                            description: 'Duration in seconds to read'
                        },
                        timeout: {
                            type: 'number',
                            description: 'Timeout in milliseconds (optional)',
                            default: 1000
                        }
                    },
                    required: ['port', 'duration']
                }
            },
            {
                name: 'serial_monitor_list_ports',
                description: 'List all available serial ports',
                inputSchema: {
                    type: 'object',
                    properties: {},
                    required: []
                }
            },
            {
                name: 'serial_monitor_session_info',
                description: 'Get information about current and historical sessions',
                inputSchema: {
                    type: 'object',
                    properties: {},
                    required: []
                }
            }
        ];
    }

    async handleToolCall(toolName: string, params: any): Promise<MCPToolResult> {
        try {
            switch (toolName) {
                case 'serial_monitor_start_async':
                    return await this.handleStartAsync(params);
                case 'serial_monitor_check':
                    return await this.handleCheck(params);
                case 'serial_monitor_send':
                    return await this.handleSend(params);
                case 'serial_monitor_cancel':
                    return await this.handleCancel(params);
                case 'serial_monitor_connect':
                    return await this.handleConnect(params);
                case 'serial_monitor_read':
                    return await this.handleRead(params);
                case 'serial_monitor_list_ports':
                    return await this.handleListPorts(params);
                case 'serial_monitor_session_info':
                    return await this.handleSessionInfo(params);
                default:
                    return {
                        success: false,
                        error: `Unknown tool: ${toolName}`
                    };
            }
        } catch (error) {
            return {
                success: false,
                error: `Tool execution failed: ${error}`
            };
        }
    }

    private async handleStartAsync(params: any): Promise<MCPToolResult> {
        const { port, watch_for, timeout_ms, buffer_lines = 100 } = params;

        if (!port || !watch_for || !timeout_ms) {
            return {
                success: false,
                error: 'Missing required parameters: port, watch_for, timeout_ms'
            };
        }

        if (!Array.isArray(watch_for)) {
            return {
                success: false,
                error: 'watch_for must be an array of strings'
            };
        }

        try {
            const config: WatchConfig = {
                port,
                watchFor: watch_for,
                timeoutMs: timeout_ms,
                bufferLines: buffer_lines
            };

            const taskId = await this.watchManager.startWatch(config);
            
            return {
                success: true,
                data: { task_id: taskId }
            };
        } catch (error) {
            return {
                success: false,
                error: `Failed to start watch: ${error}`
            };
        }
    }

    private async handleCheck(params: any): Promise<MCPToolResult> {
        const { task_id } = params;

        if (!task_id) {
            return {
                success: false,
                error: 'Missing required parameter: task_id'
            };
        }

        const status = this.watchManager.checkStatus(task_id);
        if (!status) {
            return {
                success: false,
                error: `Task not found: ${task_id}`
            };
        }

        return {
            success: true,
            data: status
        };
    }

    private async handleSend(params: any): Promise<MCPToolResult> {
        const { port, data } = params;

        if (!port || data === undefined) {
            return {
                success: false,
                error: 'Missing required parameters: port, data'
            };
        }

        try {
            // Auto-detect if port is "auto"
            let targetPort = port;
            if (port === "auto") {
                const detectedPort = await this.serialManager.detectPico();
                if (!detectedPort) {
                    return {
                        success: false,
                        error: 'No Raspberry Pi Pico device detected'
                    };
                }
                targetPort = detectedPort;
            }

            // Connect if not already connected
            if (!this.serialManager.isConnected(targetPort)) {
                await this.serialManager.connect(targetPort);
            }

            await this.serialManager.send(targetPort, data);
            
            return {
                success: true,
                data: { sent: data.length, port: targetPort }
            };
        } catch (error) {
            return {
                success: false,
                error: `Failed to send data: ${error}`
            };
        }
    }

    private async handleCancel(params: any): Promise<MCPToolResult> {
        const { task_id } = params;

        if (!task_id) {
            return {
                success: false,
                error: 'Missing required parameter: task_id'
            };
        }

        const cancelled = this.watchManager.cancelWatch(task_id);
        
        return {
            success: cancelled,
            data: { cancelled },
            error: cancelled ? undefined : `Task not found: ${task_id}`
        };
    }

    private async handleConnect(params: any): Promise<MCPToolResult> {
        const { port, baud_rate = 115200 } = params;

        if (!port) {
            return {
                success: false,
                error: 'Missing required parameter: port'
            };
        }

        try {
            // Auto-detect if port is "auto"
            let targetPort = port;
            if (port === "auto") {
                const detectedPort = await this.serialManager.detectPico();
                if (!detectedPort) {
                    return {
                        success: false,
                        error: 'No Raspberry Pi Pico device detected'
                    };
                }
                targetPort = detectedPort;
            }

            const success = await this.serialManager.connect(targetPort, baud_rate);
            
            return {
                success,
                data: { port: targetPort, baud_rate, connected: success },
                error: success ? undefined : `Failed to connect to ${targetPort}`
            };
        } catch (error) {
            return {
                success: false,
                error: `Connection failed: ${error}`
            };
        }
    }

    private async handleRead(params: any): Promise<MCPToolResult> {
        const { port, duration, timeout = 1000 } = params;

        if (!port || !duration) {
            return {
                success: false,
                error: 'Missing required parameters: port, duration'
            };
        }

        try {
            // Auto-detect if port is "auto"
            let targetPort = port;
            if (port === "auto") {
                const detectedPort = await this.serialManager.detectPico();
                if (!detectedPort) {
                    return {
                        success: false,
                        error: 'No Raspberry Pi Pico device detected'
                    };
                }
                targetPort = detectedPort;
            }

            // Ensure connection
            if (!this.serialManager.isConnected(targetPort)) {
                await this.serialManager.connect(targetPort);
            }

            const data = await this.serialManager.readForDuration(targetPort, duration * 1000);
            
            return {
                success: true,
                data: { 
                    port: targetPort, 
                    duration, 
                    lines: data.split('\n').length,
                    content: data.trim()
                }
            };
        } catch (error) {
            return {
                success: false,
                error: `Failed to read data: ${error}`
            };
        }
    }

    private async handleListPorts(params: any): Promise<MCPToolResult> {
        try {
            const ports = await this.serialManager.listPorts();
            
            return {
                success: true,
                data: { 
                    ports: ports,
                    count: ports.length
                }
            };
        } catch (error) {
            return {
                success: false,
                error: `Failed to list ports: ${error}`
            };
        }
    }

    private async handleSessionInfo(params: any): Promise<MCPToolResult> {
        try {
            const sessionInfo = this.serialManager.getSessionInfo();
            
            if (!sessionInfo) {
                return {
                    success: false,
                    error: 'No workspace available for session information'
                };
            }
            
            return {
                success: true,
                data: sessionInfo
            };
        } catch (error) {
            return {
                success: false,
                error: `Failed to get session info: ${error}`
            };
        }
    }

    // Method to expose tools for VS Code extension registration
    getToolsForRegistration(): any[] {
        return this.getTools().map(tool => ({
            name: tool.name,
            description: tool.description,
            parameters: tool.inputSchema
        }));
    }
}