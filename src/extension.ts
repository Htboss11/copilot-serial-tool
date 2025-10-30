// The module 'vscode' contains the VS Code extensibility API
// Import the module and reference it with the alias vscode in your code below
import * as vscode from 'vscode';
import { SerialManager } from './serialManager';
import { WatchManager } from './watchManager';
import { MCPServer } from './mcpServer';
import { SerialPanel } from './webview/SerialPanel';

let serialManager: SerialManager;
let watchManager: WatchManager;
let mcpServer: MCPServer;

// This method is called when your extension is activated
// Your extension is activated the very first time the command is executed
export function activate(context: vscode.ExtensionContext) {
	console.log('Serial Monitor extension is now active!');

	// Initialize managers
	serialManager = new SerialManager();
	watchManager = new WatchManager(serialManager);
	mcpServer = new MCPServer(serialManager, watchManager);

	// Register commands
	const openSerialMonitor = vscode.commands.registerCommand('serial-monitor.open', () => {
		SerialPanel.createOrShow(context.extensionUri, serialManager);
	});

	const listPorts = vscode.commands.registerCommand('serial-monitor.listPorts', async () => {
		try {
			const ports = await serialManager.listPorts();
			const portNames = ports.map(port => `${port.path}${port.manufacturer ? ` (${port.manufacturer})` : ''}`);
			
			if (portNames.length === 0) {
				vscode.window.showInformationMessage('No serial ports found');
				return;
			}

			const selected = await vscode.window.showQuickPick(portNames, {
				placeHolder: 'Select a serial port'
			});

			if (selected) {
				const selectedPort = ports.find(port => selected.startsWith(port.path));
				if (selectedPort) {
					vscode.window.showInformationMessage(`Selected port: ${selectedPort.path}`);
				}
			}
		} catch (error) {
			vscode.window.showErrorMessage(`Failed to list ports: ${error}`);
		}
	});

	const detectPico = vscode.commands.registerCommand('serial-monitor.detectPico', async () => {
		try {
			const port = await serialManager.detectPico();
			if (port) {
				vscode.window.showInformationMessage(`Raspberry Pi Pico detected on: ${port}`);
			} else {
				vscode.window.showInformationMessage('No Raspberry Pi Pico devices found');
			}
		} catch (error) {
			vscode.window.showErrorMessage(`Failed to detect Pico: ${error}`);
		}
	});

	// MCP Tool handlers
	const handleMCPTool = async (toolName: string, params: any) => {
		try {
			const result = await mcpServer.handleToolCall(toolName, params);
			return result;
		} catch (error) {
			return {
				success: false,
				error: `MCP tool execution failed: ${error}`
			};
		}
	};

	// Register MCP tools for AI agent integration
	const tools = mcpServer.getToolsForRegistration();
	for (const tool of tools) {
		const disposable = vscode.commands.registerCommand(
			`serial-monitor.mcp.${tool.name}`,
			async (params: any) => {
				return await handleMCPTool(tool.name, params);
			}
		);
		context.subscriptions.push(disposable);
	}

	// Add to subscriptions
	context.subscriptions.push(
		openSerialMonitor,
		listPorts,
		detectPico
	);

	// Cleanup on deactivation
	context.subscriptions.push({
		dispose: () => {
			if (serialManager) {
				serialManager.disconnectAll().catch(console.error);
			}
		}
	});

	// Periodic cleanup of watch tasks
	const cleanupInterval = setInterval(() => {
		if (watchManager) {
			watchManager.cleanup();
		}
	}, 60000); // Every minute

	context.subscriptions.push({
		dispose: () => clearInterval(cleanupInterval)
	});

	console.log('Serial Monitor extension activated with MCP integration');
}

// This method is called when your extension is deactivated
export function deactivate() {}
