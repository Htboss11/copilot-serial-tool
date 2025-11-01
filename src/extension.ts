import * as vscode from 'vscode';
import { SerialMonitorMcpProvider } from './mcpServerProvider';

/**
 * Copilot Serial Tool Extension v2.0
 * Provides Python daemon-based serial monitoring with MCP integration
 */

let mcpProvider: SerialMonitorMcpProvider | undefined;

export function activate(context: vscode.ExtensionContext) {
    console.log('Copilot Serial Tool extension activated');

    // Register MCP Server Provider
    try {
        mcpProvider = new SerialMonitorMcpProvider(context.extensionPath);
        const mcpDisposable = vscode.lm.registerMcpServerDefinitionProvider(
            'copilot-serial-tool.mcp-provider',
            mcpProvider
        );
        context.subscriptions.push(mcpDisposable);
        console.log('MCP Server Provider registered - daemon tools available to Copilot');
    } catch (error) {
        console.error('Failed to register MCP Server Provider:', error);
    }

    // Register status command
    const statusCommand = vscode.commands.registerCommand('copilot-serial-tool.status', () => {
        vscode.window.showInformationMessage(
            'Copilot Serial Tool Extension v2.0 - Use Copilot to control daemon'
        );
    });

    context.subscriptions.push(statusCommand);
}

export async function deactivate() {
    console.log('Copilot Serial Tool extension deactivating - stopping daemon...');
    
    // Stop the daemon when extension is deactivated
    if (mcpProvider) {
        try {
            await mcpProvider.stopDaemon();
            console.log('Daemon stopped successfully during deactivation');
        } catch (error) {
            console.error('Error stopping daemon during deactivation:', error);
        }
    }
    
    console.log('Copilot Serial Tool extension deactivated');
}
