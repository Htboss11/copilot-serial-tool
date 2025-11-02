import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { spawn } from 'child_process';

/**
 * Find a working Python executable
 * Tries common locations and verifies Python can execute
 */
function findPythonExecutable(): string {
    // Try common Python locations on Windows
    const candidates = [
        'python',      // System PATH
        'python3',     // Unix-style
        'py',          // Windows Python Launcher
    ];
    
    // Add Windows-specific paths
    if (process.platform === 'win32') {
        const programFiles = process.env['ProgramFiles'] || 'C:\\Program Files';
        const programFilesX86 = process.env['ProgramFiles(x86)'] || 'C:\\Program Files (x86)';
        const localAppData = process.env['LOCALAPPDATA'] || path.join(process.env['USERPROFILE'] || 'C:\\Users\\Default', 'AppData', 'Local');
        
        candidates.push(
            path.join(programFiles, 'Python312', 'python.exe'),
            path.join(programFiles, 'Python311', 'python.exe'),
            path.join(programFiles, 'Python310', 'python.exe'),
            path.join(localAppData, 'Programs', 'Python', 'Python312', 'python.exe'),
            path.join(localAppData, 'Programs', 'Python', 'Python311', 'python.exe'),
            path.join(localAppData, 'Programs', 'Python', 'Python310', 'python.exe'),
        );
    }
    
    // Return first candidate that exists (for full paths) or first simple command
    for (const candidate of candidates) {
        if (path.isAbsolute(candidate)) {
            if (fs.existsSync(candidate)) {
                console.log(`Found Python at: ${candidate}`);
                return candidate;
            }
        } else {
            // For commands like 'python', 'python3', we'll try them
            // (they'll be resolved by the shell)
            console.log(`Using Python command: ${candidate}`);
            return candidate;
        }
    }
    
    // Default fallback
    console.warn('No Python found, falling back to "python"');
    return 'python';
}

/**
 * Provides the Copilot Serial Tool Daemon MCP server to VS Code's language model infrastructure
 * This makes the daemon control tools available to GitHub Copilot and other AI assistants
 */
export class SerialMonitorMcpProvider implements vscode.McpServerDefinitionProvider<vscode.McpStdioServerDefinition> {
    private extensionPath: string;
    private pythonExecutable: string;

    constructor(extensionPath: string) {
        this.extensionPath = extensionPath;
        this.pythonExecutable = findPythonExecutable();
    }
    
    /**
     * Stop the daemon by calling the stop command
     * Called during extension deactivation
     */
    async stopDaemon(): Promise<void> {
        return new Promise((resolve, reject) => {
            const toolsPath = path.join(this.extensionPath, 'daemon', 'mcp_daemon_tools.py');
            
            // Use the same Python executable we use for MCP server
            const stopProcess = spawn(this.pythonExecutable, [toolsPath, 'stop'], {
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
            this.pythonExecutable,            // command - Python interpreter (consistent across windows)
            [mcpServerPath],                 // args - path to Python MCP server
            {},                              // env - environment variables
            '2.0.0'                          // version - daemon-based architecture
        );

        console.log(`📡 Providing Copilot Serial Tool Daemon MCP server (using ${this.pythonExecutable})`);
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

