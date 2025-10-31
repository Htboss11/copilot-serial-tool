import * as vscode from 'vscode';
import { SerialManager } from './serialManager';
import { WatchManager } from './watchManager';
import { MCPServer } from './mcpServer';
import { SerialPanel } from './webview/SerialPanel';
import { DependencyManager } from './dependencyManager';
import { MCPAutoRegister } from './mcpAutoRegister';
import { SerialMonitorMcpProvider } from './mcpServerProvider';

let serialManager: SerialManager;
let watchManager: WatchManager;
let mcpServer: MCPServer;

export function activate(context: vscode.ExtensionContext) {
    console.log('🔌 Serial Monitor extension is now active!');

    // Register MCP Server Provider (the proper way for VS Code MCP integration)
    try {
        const mcpProvider = new SerialMonitorMcpProvider(context.extensionPath);
        const mcpDisposable = vscode.lm.registerMcpServerDefinitionProvider(
            'serial-monitor.mcp-provider',
            mcpProvider
        );
        context.subscriptions.push(mcpDisposable);
        console.log('✅ MCP Server Provider registered successfully');
    } catch (error) {
        console.error('❌ Failed to register MCP Server Provider:', error);
    }

    // Check dependencies first
    checkDependenciesAndInitialize(context);
}

async function checkDependenciesAndInitialize(context: vscode.ExtensionContext) {
    try {
        console.log('🔍 Checking dependencies...');
        const dependencyManager = DependencyManager.getInstance();
        const status = await dependencyManager.checkDependencies();
        
        console.log('📋 Dependency status:', dependencyManager.getStatusMessage(status));

        // Always initialize the extension (even with missing dependencies)
        // This allows users to see commands and get help
        await initializeExtension(context);

        // Show notification if dependencies are missing
        if (!status.allSatisfied) {
            await dependencyManager.showDependencyNotification(status);
        } else {
            console.log('✅ All dependencies satisfied, extension fully operational');
        }

    } catch (error) {
        console.error('❌ Dependency check failed:', error);
        vscode.window.showErrorMessage(
            `Serial Monitor: Dependency check failed - ${error}`,
            'Retry'
        ).then(action => {
            if (action === 'Retry') {
                checkDependenciesAndInitialize(context);
            }
        });
        
        // Still initialize extension for basic functionality
        await initializeExtension(context);
    }
}

async function initializeExtension(context: vscode.ExtensionContext) {
    try {
        // Get workspace root for session management
        const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
        
        // Initialize managers with workspace root for session management
        serialManager = new SerialManager(context.extensionPath, workspaceRoot);
        watchManager = new WatchManager(serialManager);
        mcpServer = new MCPServer(serialManager, watchManager);

        console.log('✅ Managers initialized successfully');

        // Start background monitoring if enabled and Pico is detected
        const startBackgroundMonitoring = async () => {
            const config = vscode.workspace.getConfiguration('serialMonitor');
            const backgroundEnabled = config.get('backgroundMonitoring', true);
            
            if (backgroundEnabled) {
                try {
                    const picoPort = await serialManager.detectPico();
                    if (picoPort) {
                        console.log(`🔍 Auto-detected Pico on ${picoPort}, starting background monitoring...`);
                        const success = await serialManager.connect(picoPort);
                        if (success) {
                            console.log('✅ Background monitoring started');
                            vscode.window.showInformationMessage(
                                `Background monitoring started for ${picoPort}`,
                                'View Sessions', 'Settings'
                            ).then(selection => {
                                if (selection === 'View Sessions') {
                                    serialManager.showSessionsFolder();
                                } else if (selection === 'Settings') {
                                    vscode.commands.executeCommand('workbench.action.openSettings', 'serialMonitor');
                                }
                            });
                        }
                    } else {
                        console.log('🔍 No Pico detected for background monitoring');
                    }
                } catch (error) {
                    console.error('❌ Failed to start background monitoring:', error);
                }
            }
        };

        // Start background monitoring after a short delay
        setTimeout(startBackgroundMonitoring, 2000);

        // Register the main command with immediate COM9 connection
        const openSerialMonitor = vscode.commands.registerCommand('serial-monitor.open', async () => {
            console.log('🔌 Serial Monitor command triggered');
            try {
                // Show the webview panel immediately and auto-connect to COM9
                SerialPanel.createOrShow(context.extensionUri, serialManager, 'COM9');
                vscode.window.showInformationMessage('🚀 Serial Monitor opened for COM9 - connecting...');
            } catch (error) {
                console.error('❌ Error opening Serial Monitor:', error);
                vscode.window.showErrorMessage(`Failed to open Serial Monitor: ${error}`);
            }
        });

        console.log('✅ Command serial-monitor.open registered successfully');

        // Register session management commands
        const showSessionsCommand = vscode.commands.registerCommand('serial-monitor.showSessions', async () => {
            await serialManager.showSessionsFolder();
        });

        const sessionInfoCommand = vscode.commands.registerCommand('serial-monitor.sessionInfo', async () => {
            const info = serialManager.getSessionInfo();
            if (info) {
                const panel = vscode.window.createWebviewPanel(
                    'sessionInfo',
                    'Serial Monitor Session Info',
                    vscode.ViewColumn.One,
                    { enableScripts: false }
                );
                
                panel.webview.html = `<!DOCTYPE html>
<html><head><style>
body { font-family: var(--vscode-font-family); padding: 20px; }
.config, .session, .files { margin: 20px 0; padding: 15px; border: 1px solid var(--vscode-panel-border); }
.active { color: var(--vscode-charts-green); }
.inactive { color: var(--vscode-charts-red); }
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; padding: 8px; border-bottom: 1px solid var(--vscode-panel-border); }
</style></head><body>
<h1>Serial Monitor Session Information</h1>
<div class="config"><h2>Configuration</h2>
<p><strong>Background Monitoring:</strong> <span class="${info.config.enabled ? 'active' : 'inactive'}">${info.config.enabled ? 'Enabled' : 'Disabled'}</span></p>
<p><strong>Session Timeout:</strong> ${Math.round(info.config.timeoutSeconds/60)} minutes</p>
<p><strong>Max Session Files:</strong> ${info.config.maxFiles}</p>
<p><strong>Max File Size:</strong> ${Math.round(info.config.maxSizeBytes/1024/1024)}MB</p>
<p><strong>Session Directory:</strong> ${info.directory}</p>
</div>
<div class="session"><h2>Current Session</h2>
<p><strong>Status:</strong> <span class="${info.currentSession.active ? 'active' : 'inactive'}">${info.currentSession.active ? 'Active' : 'Inactive'}</span></p>
${info.currentSession.active ? `
<p><strong>File:</strong> ${info.currentSession.file}</p>
<p><strong>Size:</strong> ${Math.round(info.currentSession.size/1024)}KB</p>
<p><strong>Duration:</strong> ${Math.round(info.currentSession.duration/60)} minutes</p>
<p><strong>Started:</strong> ${new Date(info.currentSession.startTime).toLocaleString()}</p>
` : ''}
</div>
<div class="files"><h2>Session Files (${info.sessionFiles.length})</h2>
${info.sessionFiles.length > 0 ? `
<table><tr><th>File</th><th>Session</th><th>Size</th><th>Date</th></tr>
${info.sessionFiles.map((f: any) => `
<tr><td>${f.file}</td><td>#${f.sessionNumber}</td><td>${Math.round(f.size/1024)}KB</td><td>${new Date(f.startTime).toLocaleString()}</td></tr>
`).join('')}</table>
` : '<p>No session files found</p>'}
</div></body></html>`;
            } else {
                vscode.window.showWarningMessage('Session information not available - no workspace open');
            }
        });

        // Register dependency check command
        const checkDependenciesCommand = vscode.commands.registerCommand('serial-monitor.checkDependencies', async () => {
            const dependencyManager = DependencyManager.getInstance();
            
            vscode.window.withProgress({
                location: vscode.ProgressLocation.Notification,
                title: "Checking dependencies...",
                cancellable: false
            }, async (progress) => {
                progress.report({ increment: 0, message: "Checking Python..." });
                
                const status = await dependencyManager.checkDependencies();
                
                progress.report({ increment: 100, message: "Complete!" });
                
                const statusMessage = dependencyManager.getStatusMessage(status);
                
                if (status.allSatisfied) {
                    vscode.window.showInformationMessage(
                        `${statusMessage} - Serial Monitor is ready!`,
                        'Open Serial Monitor'
                    ).then(action => {
                        if (action === 'Open Serial Monitor') {
                            vscode.commands.executeCommand('serial-monitor.open');
                        }
                    });
                } else {
                    await dependencyManager.showDependencyNotification(status);
                }
            });
        });

        // Listen for configuration changes
        const configChangeListener = vscode.workspace.onDidChangeConfiguration((e) => {
            if (e.affectsConfiguration('serialMonitor')) {
                serialManager.onConfigurationChanged();
            }
        });

        // Register MCP tools for AI agent integration
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

        // Register Language Model Tools for GitHub Copilot integration
        if (vscode.lm?.registerTool) {
            console.log('🤖 Registering Language Model Tools for GitHub Copilot...');
            
            // Create tool handlers
            const toolHandlers = {
                serial_monitor_connect: async (params: { port: string; baud_rate?: number }) => {
                    const result = await handleMCPTool('connect', params);
                    return { result: result.data || (result.success ? 'Connected successfully' : result.error) };
                },
                serial_monitor_send: async (params: { port: string; data: string }) => {
                    const result = await handleMCPTool('send', params);
                    return { result: result.data || (result.success ? 'Data sent successfully' : result.error) };
                },
                serial_monitor_read: async (params: { port: string; duration: number; timeout?: number }) => {
                    const result = await handleMCPTool('read', params);
                    return { result: result.data || (result.success ? 'No data received' : result.error) };
                },
                serial_monitor_list_ports: async () => {
                    const result = await handleMCPTool('list_ports', {});
                    return { result: result.data || (result.success ? 'No ports found' : result.error) };
                },
                serial_monitor_session_info: async () => {
                    const result = await handleMCPTool('session_info', {});
                    return { result: result.data || (result.success ? 'No session information' : result.error) };
                },
                serial_monitor_start_watch: async (params: { port: string; watch_for: string[]; timeout_ms: number; buffer_lines?: number }) => {
                    const result = await handleMCPTool('start_watch', params);
                    return { result: result.data || (result.success ? 'Watch started' : result.error) };
                },
                serial_monitor_check_watch: async (params: { task_id: string }) => {
                    const result = await handleMCPTool('check_watch', params);
                    return { result: result.data || (result.success ? 'No watch status' : result.error) };
                },
                serial_monitor_stop_watch: async (params: { task_id: string }) => {
                    const result = await handleMCPTool('stop_watch', params);
                    return { result: result.data || (result.success ? 'Watch stopped' : result.error) };
                }
            };

            // Register all tools
            for (const [toolName, handler] of Object.entries(toolHandlers)) {
                try {
                    const tool = vscode.lm.registerTool(toolName, handler as any);
                    context.subscriptions.push(tool);
                    console.log(`✅ Registered Language Model Tool: ${toolName}`);
                } catch (error) {
                    console.error(`❌ Failed to register tool ${toolName}:`, error);
                }
            }
            
            console.log('🎉 Language Model Tools registration complete!');
        } else {
            console.log('⚠️ Language Model Tools API not available (VS Code version may be too old)');
        }

        // Add to subscriptions
        context.subscriptions.push(
            openSerialMonitor,
            showSessionsCommand,
            sessionInfoCommand,
            checkDependenciesCommand,
            configChangeListener
        );

        // Cleanup on deactivation
        context.subscriptions.push({
            dispose: () => {
                if (serialManager) {
                    serialManager.dispose();
                }
            }
        });

        console.log('✅ Serial Monitor extension activated with MCP integration');
        
        // Automatically register MCP server in settings
        console.log('🔌 Auto-registering MCP server...');
        const mcpAutoRegister = new MCPAutoRegister(context.extensionPath);
        await mcpAutoRegister.autoRegister();
        
    } catch (error) {
        console.error('❌ Extension activation failed:', error);
        vscode.window.showErrorMessage(`Serial Monitor extension failed to activate: ${error}`);
    }
}

export function deactivate() {
    console.log('Serial Monitor extension deactivated');
}