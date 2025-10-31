#!/usr/bin/env node
/**
 * MCP Server Entry Point for VS Code Serial Monitor
 * This creates a standalone MCP server that AI agents can connect to
 */

import { MCPServer } from './mcpServer';
import { SerialManager } from './serialManager';
import { WatchManager } from './watchManager';
import * as path from 'path';

class StandaloneMCPServer {
    private mcpServer: MCPServer;
    private serialManager: SerialManager;
    private watchManager: WatchManager;

    constructor() {
        // Initialize managers (no VS Code context needed for MCP server)
        const extensionPath = path.dirname(__filename);
        this.serialManager = new SerialManager(extensionPath);
        this.watchManager = new WatchManager(this.serialManager);
        this.mcpServer = new MCPServer(this.serialManager, this.watchManager);
        
        this.setupStdioInterface();
    }

    private setupStdioInterface(): void {
        // Handle MCP protocol over stdio
        process.stdin.setEncoding('utf8');
        process.stdin.on('readable', () => {
            const chunk = process.stdin.read();
            if (chunk !== null) {
                this.handleMCPRequest(chunk.toString().trim());
            }
        });

        // Send initialization message
        this.sendMCPResponse({
            jsonrpc: '2.0',
            result: {
                protocolVersion: '2024-11-05',
                capabilities: {
                    tools: true
                },
                serverInfo: {
                    name: 'serial-monitor-mcp',
                    version: '1.0.0'
                }
            }
        });
    }

    private async handleMCPRequest(request: string): Promise<void> {
        try {
            const req = JSON.parse(request);
            
            if (req.method === 'tools/list') {
                const tools = this.mcpServer.getTools();
                this.sendMCPResponse({
                    jsonrpc: '2.0',
                    id: req.id,
                    result: { tools }
                });
            } else if (req.method === 'tools/call') {
                const result = await this.mcpServer.handleToolCall(req.params.name, req.params.arguments || {});
                this.sendMCPResponse({
                    jsonrpc: '2.0',
                    id: req.id,
                    result: { content: [{ type: 'text', text: JSON.stringify(result) }] }
                });
            } else {
                this.sendMCPResponse({
                    jsonrpc: '2.0',
                    id: req.id,
                    error: { code: -32601, message: 'Method not found' }
                });
            }
        } catch (error) {
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
}

// Start the MCP server
new StandaloneMCPServer();