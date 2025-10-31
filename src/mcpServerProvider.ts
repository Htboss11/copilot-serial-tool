import * as vscode from 'vscode';
import * as path from 'path';

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

