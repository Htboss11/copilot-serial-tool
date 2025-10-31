import * as path from 'path';
import { spawn, ChildProcess } from 'child_process';
import { SessionManager } from './sessionManager';

// Make vscode optional for MCP standalone usage
let vscode: any = null;
try {
    vscode = require('vscode');
} catch (e) {
    // Running in MCP standalone mode without VS Code
    console.log('Running in MCP standalone mode (no VS Code API available)');
}

export interface SerialPortInfo {
    path: string;
    description?: string;
    manufacturer?: string;
    vid?: number;
    pid?: number;
    serialNumber?: string;
}

export interface BufferEntry {
    timestamp: string;
    data: string;
}

export interface BufferResult {
    success: boolean;
    port?: string;
    buffer_seconds?: number;
    total_lines?: number;
    data?: BufferEntry[];
    error?: string;
}

/**
 * Circular buffer that stores data with timestamps
 * Automatically expires entries older than maxSeconds
 */
class CircularBuffer {
    private buffer: BufferEntry[] = [];
    private readonly maxSeconds: number;

    constructor(maxSeconds: number = 600) {
        this.maxSeconds = maxSeconds;
    }

    /**
     * Add a new entry to the buffer
     */
    add(timestamp: string, data: string): void {
        this.buffer.push({ timestamp, data });
        this.cleanup();
    }

    /**
     * Get all buffered entries (after cleanup)
     */
    getAll(): BufferEntry[] {
        this.cleanup();
        return [...this.buffer];
    }

    /**
     * Get entries from the last N seconds
     */
    getRecent(seconds: number): BufferEntry[] {
        this.cleanup();
        const cutoffTime = Date.now() - (seconds * 1000);
        return this.buffer.filter(entry => {
            const entryTime = new Date(entry.timestamp).getTime();
            return entryTime >= cutoffTime;
        });
    }

    /**
     * Clear all entries
     */
    clear(): void {
        this.buffer = [];
    }

    /**
     * Remove entries older than maxSeconds
     */
    private cleanup(): void {
        const cutoffTime = Date.now() - (this.maxSeconds * 1000);
        this.buffer = this.buffer.filter(entry => {
            const entryTime = new Date(entry.timestamp).getTime();
            return entryTime >= cutoffTime;
        });
    }

    /**
     * Get current buffer size
     */
    size(): number {
        this.cleanup();
        return this.buffer.length;
    }
}

export class SerialManager {
    private activeConnections: Map<string, ChildProcess> = new Map();
    private outputChannels: Map<string, any> = new Map(); // vscode.OutputChannel or null in MCP mode
    private buffers: Map<string, CircularBuffer> = new Map();
    private pythonScriptPath: string;
    private sessionManager: SessionManager | null = null;

    constructor(extensionPath: string, workspaceRoot?: string) {
        this.pythonScriptPath = path.join(extensionPath, 'python', 'serial_monitor.py');
        // Debug flag: allow enabling Python-side debug logging via env var
        (this as any).debug = process.env.SERIAL_MONITOR_DEBUG === '1';
        
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
            if (this.activeConnections.has(portPath)) {
                console.log(`Port ${portPath} is already connected`);
                return true;
            }

            // Create output channel for this port (if running in VS Code)
            let outputChannel: any = null;
            if (vscode) {
                outputChannel = vscode.window.createOutputChannel(`Serial Monitor - ${portPath}`);
                this.outputChannels.set(portPath, outputChannel);
            }

            // Create circular buffer for this port (600 seconds = 10 minutes)
            const buffer = new CircularBuffer(600);
            this.buffers.set(portPath, buffer);

            // Add connection marker to buffer
            const connectTimestamp = new Date().toISOString();
            buffer.add(connectTimestamp, '=== CONNECTION ESTABLISHED ===');

            // Start Python process for continuous monitoring
            const python = spawn('python', [
                this.pythonScriptPath, 
                'connect', 
                '--port', portPath, 
                '--baud', baudRate.toString()
            ], {
                stdio: ['pipe', 'pipe', 'pipe'],
                // Force-enable SERIAL_MONITOR_DEBUG for diagnostic runs; set to '0' in production if needed
                env: Object.assign({}, process.env, { 
                    SERIAL_MONITOR_DEBUG: '1',
                    SERIAL_MONITOR_DEBUG_PATH: path.join(path.dirname(this.pythonScriptPath), 'serial_debug.log')
                })
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
                                if (outputChannel) {
                                    outputChannel.appendLine(message);
                                } else {
                                    console.log(message);
                                }
                                console.log(`Data from ${portPath}:`, parsed.data);
                                
                                // Add to buffer
                                buffer.add(parsed.timestamp, parsed.data);
                                
                                // Log to session file
                                if (this.sessionManager) {
                                    this.sessionManager.logData(portPath, parsed.timestamp, parsed.data);
                                }
                            } else if (parsed.type === 'error') {
                                if (outputChannel) {
                                    outputChannel.appendLine(`[ERROR] ${parsed.error}`);
                                } else {
                                    console.error(`[ERROR] ${parsed.error}`);
                                }
                                console.error(`Serial error on ${portPath}:`, parsed.error);
                                
                                // Add error to buffer
                                const errorTimestamp = new Date().toISOString();
                                buffer.add(errorTimestamp, `ERROR: ${parsed.error}`);
                                
                                // Log errors to session file too
                                if (this.sessionManager) {
                                    this.sessionManager.logData(portPath, errorTimestamp, `ERROR: ${parsed.error}`);
                                }
                            }
                        } catch (parseError) {
                            // Handle non-JSON output
                            const timestamp = new Date().toISOString();
                            outputChannel.appendLine(`[${timestamp}] ${line.trim()}`);
                            
                            // Add raw output to buffer
                            buffer.add(timestamp, `RAW: ${line.trim()}`);
                            
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
                
                // Add disconnection marker to buffer
                if (this.buffers.has(portPath)) {
                    const disconnectTimestamp = new Date().toISOString();
                    const marker = code === 0 ? '=== DISCONNECTED BY USER ===' : '=== CONNECTION LOST ===';
                    this.buffers.get(portPath)!.add(disconnectTimestamp, marker);
                    
                    // Log to session file
                    if (this.sessionManager) {
                        this.sessionManager.logData(portPath, disconnectTimestamp, marker);
                    }
                }
                
                this.activeConnections.delete(portPath);
                this.outputChannels.delete(portPath);
                // Keep buffer for potential reconnection or later retrieval
                
                // End session when connection closes
                if (this.sessionManager) {
                    this.sessionManager.endSession();
                }
            });

            python.on('error', (error) => {
                console.error(`Python process error for ${portPath}:`, error);
                outputChannel.appendLine(`[ERROR] Process error: ${error.message}`);
                vscode?.window?.showErrorMessage(`Serial process error: ${error.message}`);
                
                // Add error marker to buffer
                if (this.buffers.has(portPath)) {
                    const errorTimestamp = new Date().toISOString();
                    this.buffers.get(portPath)!.add(errorTimestamp, `=== ERROR: ${error.message} ===`);
                    
                    // Log to session file
                    if (this.sessionManager) {
                        this.sessionManager.logData(portPath, errorTimestamp, `ERROR: ${error.message}`);
                    }
                }
                
                // End session on error
                if (this.sessionManager) {
                    this.sessionManager.endSession();
                }
            });

            this.activeConnections.set(portPath, python);

            // Wait a moment to see if connection succeeds
            await new Promise(resolve => setTimeout(resolve, 1000));

            if (this.activeConnections.has(portPath)) {
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
            vscode?.window?.showErrorMessage(`Failed to connect to ${portPath}: ${error}`);
            return false;
        }
    }

    public async disconnect(portPath: string): Promise<boolean> {
        try {
            const process = this.activeConnections.get(portPath);
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

            this.activeConnections.delete(portPath);
            this.outputChannels.delete(portPath);

            console.log(`Disconnected from ${portPath}`);
            return true;

        } catch (error) {
            console.error(`Failed to disconnect from ${portPath}:`, error);
            vscode?.window?.showErrorMessage(`Failed to disconnect from ${portPath}: ${error}`);
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
            vscode?.window?.showErrorMessage(`Failed to send data: ${error}`);
            return false;
        }
    }

    public isConnected(portPath: string): boolean {
        const process = this.activeConnections.get(portPath);
        return !!(process && !process.killed);
    }

    public getConnectedPorts(): string[] {
        return Array.from(this.activeConnections.keys()).filter(portPath => 
            this.isConnected(portPath)
        );
    }

    /**
     * Get buffered data for a port
     * @param portPath Serial port path
     * @param seconds Optional: get only last N seconds of data
     * @returns Buffer result with data entries
     */
    public async getBuffer(portPath: string, seconds?: number): Promise<BufferResult> {
        try {
            const buffer = this.buffers.get(portPath);
            
            if (!buffer) {
                return {
                    success: false,
                    error: `No buffer found for port ${portPath}. Connect first.`
                };
            }

            const data = seconds !== undefined ? buffer.getRecent(seconds) : buffer.getAll();

            return {
                success: true,
                port: portPath,
                buffer_seconds: 600,
                total_lines: data.length,
                data
            };

        } catch (error) {
            return {
                success: false,
                error: `Failed to get buffer: ${error}`
            };
        }
    }

    /**
     * Read data from port for a specified duration
     * Returns buffered data including historical data
     * @param portPath Serial port path
     * @param duration Duration in seconds to wait for data
     * @returns Buffer result with all accumulated data
     */
    public async read(portPath: string, duration: number = 5): Promise<BufferResult> {
        try {
            if (!this.isConnected(portPath)) {
                return {
                    success: false,
                    error: `Port ${portPath} not connected. Use connect first.`
                };
            }

            const buffer = this.buffers.get(portPath);
            if (!buffer) {
                return {
                    success: false,
                    error: `No buffer for port ${portPath}`
                };
            }

            // Get initial buffer size
            const initialSize = buffer.size();

            // Wait for specified duration
            await new Promise(resolve => setTimeout(resolve, duration * 1000));

            // Get all data (including historical)
            const allData = buffer.getAll();
            const newLines = allData.length - initialSize;

            console.log(`Read from ${portPath}: ${allData.length} total lines, ${newLines} new lines during ${duration}s`);

            return {
                success: true,
                port: portPath,
                buffer_seconds: 600,
                total_lines: allData.length,
                data: allData
            };

        } catch (error) {
            return {
                success: false,
                error: `Failed to read from ${portPath}: ${error}`
            };
        }
    }

    public dispose(): void {
        // Kill all Python processes
        for (const [portPath, process] of this.activeConnections) {
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

        this.activeConnections.clear();
        this.outputChannels.clear();
    }

    public getSessionInfo(): any {
        return this.sessionManager?.getSessionInfo() || null;
    }

    public async showSessionsFolder(): Promise<void> {
        if (this.sessionManager) {
            await this.sessionManager.showSessionsFolder();
        } else {
            vscode?.window?.showWarningMessage('Session manager not available - no workspace open');
        }
    }

    public onConfigurationChanged(): void {
        if (this.sessionManager) {
            this.sessionManager.onConfigurationChanged();
        }
    }

    public async readForDuration(portPath: string, durationMs: number): Promise<string> {
        return new Promise((resolve, reject) => {
            const connection = this.activeConnections.get(portPath);
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


