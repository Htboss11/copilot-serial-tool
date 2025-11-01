import * as vscode from 'vscode';
import * as path from 'path';
import { spawn } from 'child_process';

/**
 * Provides the Copilot Serial Tool Daemon MCP server to VS Code's language model infrastructure
 * This makes the daemon control tools available to GitHub Copilot and other AI assistants
 */
export class SerialMonitorMcpProvider implements vscode.McpServerDefinitionProvider<vscode.McpStdioServerDefinition> {
    private extensionPath: string;

    constructor(extensionPath: string) {
        this.extensionPath = extensionPath;
    }
    
    /**
     * Stop the daemon by calling the stop command
     * Called during extension deactivation
     */
    async stopDaemon(): Promise<void> {
        return new Promise((resolve, reject) => {
            const toolsPath = path.join(this.extensionPath, 'daemon', 'mcp_daemon_tools.py');
            
            // Call the daemon stop command
            const stopProcess = spawn('python', [toolsPath, 'stop'], {
                cwd: path.join(this.extensionPath, 'daemon')
            });
            
            let output = '';
            let errorOutput = '';
            
            stopProcess.stdout?.on('data', (data) => {
                output += data.toString();
            });
            
            stopProcess.stderr?.on('data', (data) => {
                errorOutput += data.toString();
            });
            
            stopProcess.on('close', (code) => {
                if (code === 0) {
                    console.log('Daemon stopped successfully:', output);
                    resolve();
                } else {
                    console.error('Failed to stop daemon:', errorOutput);
                    // Resolve anyway - don't block extension deactivation
                    resolve();
                }
            });
            
            // Timeout after 5 seconds
            setTimeout(() => {
                stopProcess.kill();
                console.log('Daemon stop command timed out');
                resolve();
            }, 5000);
        });
    }

    /**
     * Provides the Serial Monitor Daemon MCP server definition
     * This is called eagerly by VS Code to discover available MCP servers
     */
    provideMcpServerDefinitions(
        token: vscode.CancellationToken
    ): vscode.ProviderResult<vscode.McpStdioServerDefinition[]> {
        
        // Path to Python bootstrap script for daemon (includes vendored dependencies)
        const mcpServerPath = path.join(this.extensionPath, 'daemon', 'bootstrap.py');
        
        // Create the MCP server definition for Python daemon
        const server = new vscode.McpStdioServerDefinition(
            'Copilot Serial Tool Daemon',    // label - shown in UI
            'python',                         // command - Python interpreter
            [mcpServerPath],                 // args - path to Python MCP server
            {},                              // env - environment variables
            '2.0.0'                          // version - daemon-based architecture
        );

        console.log('📡 Providing Copilot Serial Tool Daemon MCP server');
        console.log('   Path:', mcpServerPath);
        
        return [server];
    }

    /**
     * Optional: Resolve the server definition before starting
     * Can be used for authentication, validation, etc.
     */
    resolveMcpServerDefinition?(
        server: vscode.McpStdioServerDefinition,
        token: vscode.CancellationToken
    ): vscode.ProviderResult<vscode.McpStdioServerDefinition> {
        console.log('🔧 Resolving Copilot Serial Tool MCP server:', server.label);
        
        // Return the server as-is (no additional setup needed)
        return server;
    }
}

