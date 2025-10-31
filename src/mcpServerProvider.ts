import * as vscode from 'vscode';
import * as path from 'path';

/**
 * Provides the Serial Monitor MCP server to VS Code's language model infrastructure
 * This makes the serial monitor tools available to GitHub Copilot and other AI assistants
 */
export class SerialMonitorMcpProvider implements vscode.McpServerDefinitionProvider<vscode.McpStdioServerDefinition> {
    private extensionPath: string;

    constructor(extensionPath: string) {
        this.extensionPath = extensionPath;
    }

    /**
     * Provides the Serial Monitor MCP server definition
     * This is called eagerly by VS Code to discover available MCP servers
     */
    provideMcpServerDefinitions(
        token: vscode.CancellationToken
    ): vscode.ProviderResult<vscode.McpStdioServerDefinition[]> {
        
        const mcpServerPath = path.join(this.extensionPath, 'dist', 'mcp-server-pure.js');
        
        // Create the MCP server definition
        const server = new vscode.McpStdioServerDefinition(
            'Serial Monitor',           // label - shown in UI
            'node',                      // command
            [mcpServerPath],            // args
            {},                          // env
            '1.0.0'                     // version
        );

        console.log('📡 Providing Serial Monitor MCP server definition');
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
        console.log('🔧 Resolving Serial Monitor MCP server:', server.label);
        
        // We could do additional setup here if needed
        // For now, just return the server as-is
        return server;
    }
}
