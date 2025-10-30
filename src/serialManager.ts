import * as vscode from 'vscode';
import * as path from 'path';
import { spawn, ChildProcess } from 'child_process';
import { SessionManager } from './sessionManager';

export interface SerialPortInfo {
    path: string;
    description?: string;
    manufacturer?: string;
    vid?: number;
    pid?: number;
    serialNumber?: string;
}

export class SerialManager {
    private connections: Map<string, ChildProcess> = new Map();
    private outputChannels: Map<string, vscode.OutputChannel> = new Map();
    private pythonScriptPath: string;
    private sessionManager: SessionManager | null = null;

    constructor(extensionPath: string, workspaceRoot?: string) {
        this.pythonScriptPath = path.join(extensionPath, 'python', 'serial_monitor.py');
        
        // Initialize session manager if workspace is available
        if (workspaceRoot) {
            this.sessionManager = new SessionManager(workspaceRoot);
        }
    }

    private async runPythonCommand(command: string[], options: any = {}): Promise<any> {
        return new Promise((resolve, reject) => {
            const python = spawn('python', [this.pythonScriptPath, ...command], {
                stdio: ['pipe', 'pipe', 'pipe'],
                ...options
            });

            let stdout = '';
            let stderr = '';

            python.stdout.on('data', (data) => {
                stdout += data.toString();
            });

            python.stderr.on('data', (data) => {
                stderr += data.toString();
            });

            python.on('close', (code) => {
                if (code === 0) {
                    try {
                        const result = JSON.parse(stdout.trim());
                        resolve(result);
                    } catch (error) {
                        reject(new Error(`Failed to parse JSON: ${stdout}`));
                    }
                } else {
                    reject(new Error(`Python script failed with code ${code}: ${stderr}`));
                }
            });

            python.on('error', (error) => {
                reject(new Error(`Failed to start Python script: ${error.message}`));
            });
        });
    }

    public async listPorts(): Promise<SerialPortInfo[]> {
        try {
            const result = await this.runPythonCommand(['list']);
            return result || [];
        } catch (error) {
            console.error('Error listing ports:', error);
            throw new Error(`Failed to list serial ports: ${error}`);
        }
    }

    public async detectPico(): Promise<string | null> {
        try {
            const result = await this.runPythonCommand(['detect-pico']);
            return result.pico_port || null;
        } catch (error) {
            console.error('Error detecting Pico:', error);
            return null;
        }
    }

    public async connect(portPath: string, baudRate: number = 115200): Promise<boolean> {
        try {
            if (this.connections.has(portPath)) {
                console.log(`Port ${portPath} is already connected`);
                return true;
            }

            // Create output channel for this port
            const outputChannel = vscode.window.createOutputChannel(`Serial Monitor - ${portPath}`);
            this.outputChannels.set(portPath, outputChannel);

            // Start Python process for continuous monitoring
            const python = spawn('python', [
                this.pythonScriptPath, 
                'connect', 
                '--port', portPath, 
                '--baud', baudRate.toString()
            ], {
                stdio: ['pipe', 'pipe', 'pipe']
            });

            // Handle data from Python script
            python.stdout.on('data', (data) => {
                const lines = data.toString().split('\n');
                for (const line of lines) {
                    if (line.trim()) {
                        try {
                            const parsed = JSON.parse(line);
                            if (parsed.type === 'data') {
                                const message = `[${parsed.timestamp}] ${parsed.data}`;
                                outputChannel.appendLine(message);
                                console.log(`Data from ${portPath}:`, parsed.data);
                                
                                // Log to session file
                                if (this.sessionManager) {
                                    this.sessionManager.logData(portPath, parsed.timestamp, parsed.data);
                                }
                            } else if (parsed.type === 'error') {
                                outputChannel.appendLine(`[ERROR] ${parsed.error}`);
                                console.error(`Serial error on ${portPath}:`, parsed.error);
                                
                                // Log errors to session file too
                                if (this.sessionManager) {
                                    this.sessionManager.logData(portPath, new Date().toISOString(), `ERROR: ${parsed.error}`);
                                }
                            }
                        } catch (parseError) {
                            // Handle non-JSON output
                            const timestamp = new Date().toISOString();
                            outputChannel.appendLine(`[${timestamp}] ${line.trim()}`);
                            
                            // Log raw output to session file
                            if (this.sessionManager) {
                                this.sessionManager.logData(portPath, timestamp, `RAW: ${line.trim()}`);
                            }
                        }
                    }
                }
            });

            // Handle errors
            python.stderr.on('data', (data) => {
                const error = data.toString().trim();
                outputChannel.appendLine(`[ERROR] ${error}`);
                console.error(`Serial stderr on ${portPath}:`, error);
            });

            // Handle process exit
            python.on('close', (code) => {
                console.log(`Python serial process for ${portPath} exited with code ${code}`);
                outputChannel.appendLine(`[INFO] Connection closed (exit code: ${code})`);
                this.connections.delete(portPath);
                this.outputChannels.delete(portPath);
                
                // End session when connection closes
                if (this.sessionManager) {
                    this.sessionManager.endSession();
                }
            });

            python.on('error', (error) => {
                console.error(`Python process error for ${portPath}:`, error);
                outputChannel.appendLine(`[ERROR] Process error: ${error.message}`);
                vscode.window.showErrorMessage(`Serial process error: ${error.message}`);
                
                // End session on error
                if (this.sessionManager) {
                    this.sessionManager.endSession();
                }
            });

            this.connections.set(portPath, python);

            // Wait a moment to see if connection succeeds
            await new Promise(resolve => setTimeout(resolve, 1000));

            if (this.connections.has(portPath)) {
                console.log(`Connected to ${portPath} at ${baudRate} baud`);
                outputChannel.show();
                
                // Start session logging
                if (this.sessionManager) {
                    this.sessionManager.startSession(portPath);
                }
                
                return true;
            } else {
                throw new Error('Connection failed');
            }

        } catch (error) {
            console.error(`Failed to connect to ${portPath}:`, error);
            vscode.window.showErrorMessage(`Failed to connect to ${portPath}: ${error}`);
            return false;
        }
    }

    public async disconnect(portPath: string): Promise<boolean> {
        try {
            const process = this.connections.get(portPath);
            if (!process) {
                console.log(`Port ${portPath} is not connected`);
                return true;
            }

            // Terminate the Python process
            process.kill('SIGTERM');
            
            // Clean up output channel
            const outputChannel = this.outputChannels.get(portPath);
            if (outputChannel) {
                outputChannel.dispose();
            }

            this.connections.delete(portPath);
            this.outputChannels.delete(portPath);

            console.log(`Disconnected from ${portPath}`);
            return true;

        } catch (error) {
            console.error(`Failed to disconnect from ${portPath}:`, error);
            vscode.window.showErrorMessage(`Failed to disconnect from ${portPath}: ${error}`);
            return false;
        }
    }

    public async send(portPath: string, data: string): Promise<boolean> {
        try {
            const result = await this.runPythonCommand([
                'send',
                '--port', portPath,
                '--data', data
            ]);

            if (result.success) {
                console.log(`Sent to ${portPath}:`, data);
                
                // Also log to output channel
                const outputChannel = this.outputChannels.get(portPath);
                if (outputChannel) {
                    const timestamp = new Date().toISOString();
                    outputChannel.appendLine(`[${timestamp}] SENT: ${data}`);
                }
                
                return true;
            } else {
                throw new Error(result.error);
            }

        } catch (error) {
            console.error(`Failed to send data to ${portPath}:`, error);
            vscode.window.showErrorMessage(`Failed to send data: ${error}`);
            return false;
        }
    }

    public isConnected(portPath: string): boolean {
        const process = this.connections.get(portPath);
        return !!(process && !process.killed);
    }

    public getConnectedPorts(): string[] {
        return Array.from(this.connections.keys()).filter(portPath => 
            this.isConnected(portPath)
        );
    }

    public dispose(): void {
        // Kill all Python processes
        for (const [portPath, process] of this.connections) {
            try {
                process.kill('SIGTERM');
            } catch (error) {
                console.error(`Error killing process for port ${portPath}:`, error);
            }
        }

        // Dispose all output channels
        for (const [portPath, outputChannel] of this.outputChannels) {
            try {
                outputChannel.dispose();
            } catch (error) {
                console.error(`Error disposing output channel for ${portPath}:`, error);
            }
        }

        // Dispose session manager
        if (this.sessionManager) {
            this.sessionManager.dispose();
        }

        this.connections.clear();
        this.outputChannels.clear();
    }

    public getSessionInfo(): any {
        return this.sessionManager?.getSessionInfo() || null;
    }

    public async showSessionsFolder(): Promise<void> {
        if (this.sessionManager) {
            await this.sessionManager.showSessionsFolder();
        } else {
            vscode.window.showWarningMessage('Session manager not available - no workspace open');
        }
    }

    public onConfigurationChanged(): void {
        if (this.sessionManager) {
            this.sessionManager.onConfigurationChanged();
        }
    }

    public async readForDuration(portPath: string, durationMs: number): Promise<string> {
        return new Promise((resolve, reject) => {
            const connection = this.connections.get(portPath);
            if (!connection) {
                reject(new Error(`No connection found for port ${portPath}`));
                return;
            }

            let output = '';
            const timeout = setTimeout(() => {
                connection.stdout?.removeAllListeners('data');
                resolve(output);
            }, durationMs);

            const dataHandler = (data: Buffer) => {
                output += data.toString();
            };

            connection.stdout?.on('data', dataHandler);

            // Cleanup timeout if connection ends early
            connection.on('close', () => {
                clearTimeout(timeout);
                connection.stdout?.removeAllListeners('data');
                resolve(output);
            });
        });
    }
}