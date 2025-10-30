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

    // Method to expose tools for VS Code extension registration
    getToolsForRegistration(): any[] {
        return this.getTools().map(tool => ({
            name: tool.name,
            description: tool.description,
            parameters: tool.inputSchema
        }));
    }
}