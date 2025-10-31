import * as vscode from 'vscode';
import * as path from 'path';

/**
 * MCP Server Definition Provider for GitHub Copilot
 * This registers our serial monitor MCP server with VS Code's language model API
 */
export class SerialMonitorMcpProvider implements vscode.McpServerDefinitionProvider<vscode.McpStdioServerDefinition> {
    private extensionPath: string;

    constructor(extensionPath: string) {
        this.extensionPath = extensionPath;
    }

    /**
     * Provide the MCP server definition to GitHub Copilot
     */
    provideMcpServerDefinitions(
        _token: vscode.CancellationToken
    ): vscode.ProviderResult<vscode.McpStdioServerDefinition[]> {
        const mcpServerPath = path.join(this.extensionPath, 'dist', 'mcp-server-pure.js');
        
        // Create the MCP server definition
        const serverDefinition = new vscode.McpStdioServerDefinition(
            'Serial Monitor',           // label - shown to user
            'node',                     // command
            [mcpServerPath],           // args
            {},                        // env
            '1.0.0'                    // version
        );

        return [serverDefinition];
    }
}

/**
 * Register the MCP server provider with VS Code
 */
export function registerMcpServerProvider(context: vscode.ExtensionContext): void {
    try {
        const provider = new SerialMonitorMcpProvider(context.extensionPath);
        
        // Register with the language model API
        const registration = vscode.lm.registerMcpServerDefinitionProvider(
            'htboss11.serial-monitor',  // unique identifier
            provider
        );

        context.subscriptions.push(registration);
        
        console.log('✅ Serial Monitor MCP server registered with GitHub Copilot');
    } catch (error) {
        console.error('❌ Failed to register MCP server:', error);
    }
}
