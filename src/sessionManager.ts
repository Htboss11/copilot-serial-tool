import * as fs from 'fs';
import * as path from 'path';

// Make vscode optional for MCP standalone usage
let vscode: any = null;
try {
    vscode = require('vscode');
} catch (e) {
    // Running in MCP standalone mode without VS Code
    console.log('SessionManager: Running in MCP standalone mode');
}

export interface SessionFile {
    path: string;
    sessionNumber: number;
    startTime: Date;
    endTime?: Date;
    size: number;
}

export interface SessionConfig {
    enabled: boolean;
    maxFiles: number;
    maxSizeBytes: number;
    timeoutSeconds: number;
    directory: string;
    flushIntervalSeconds: number;
}

export class SessionManager {
    private currentSessionFile: string | null = null;
    private currentSessionStream: fs.WriteStream | null = null;
    private sessionStartTime: Date | null = null;
    private sessionTimeoutHandle: NodeJS.Timeout | null = null;
    private flushIntervalHandle: NodeJS.Timeout | null = null;
    private sessionDirectory: string;
    private dataBuffer: string[] = [];
    private config: SessionConfig = {
        enabled: true,
        maxFiles: 10,
        maxSizeBytes: 10 * 1024 * 1024,
        timeoutSeconds: 3600,
        directory: 'serial-sessions',
        flushIntervalSeconds: 2
    };

    constructor(private workspaceRoot: string) {
        this.updateConfig();
        this.sessionDirectory = path.join(this.workspaceRoot, this.config.directory);
        this.ensureSessionDirectory();
    }

    private updateConfig(): void {
        const config = vscode?.workspace?.getConfiguration('serialMonitor');
        this.config = {
            enabled: config?.get('backgroundMonitoring', true) ?? true,
            maxFiles: config?.get('maxSessionFiles', 10) ?? 10,
            maxSizeBytes: (config?.get('maxFileSize', 10) ?? 10) * 1024 * 1024, // Convert MB to bytes
            timeoutSeconds: config?.get('sessionTimeout', 3600) ?? 3600,
            directory: config?.get('sessionDirectory', 'serial-sessions') ?? 'serial-sessions',
            flushIntervalSeconds: config.get('sessionFlushInterval', 2)
        };
    }

    private ensureSessionDirectory(): void {
        try {
            if (!fs.existsSync(this.sessionDirectory)) {
                fs.mkdirSync(this.sessionDirectory, { recursive: true });
                console.log(`Created session directory: ${this.sessionDirectory}`);
            }
        } catch (error) {
            console.error('Failed to create session directory:', error);
            vscode?.window?.showErrorMessage(`Failed to create session directory: ${error}`);
        }
    }

    public startSession(portPath: string): void {
        if (!this.config.enabled) {
            console.log('Background monitoring is disabled');
            return;
        }

        try {
            // Close existing session if any
            this.endSession();

            // Rotate existing files
            this.rotateSessionFiles();

            // Create new session file
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
            const sessionFileName = `session-1-${timestamp}-${portPath.replace(':', '')}.log`;
            this.currentSessionFile = path.join(this.sessionDirectory, sessionFileName);
            
            // Create write stream
            this.currentSessionStream = fs.createWriteStream(this.currentSessionFile, { flags: 'a' });
            this.sessionStartTime = new Date();

            // Write session header
            const header = `
# Serial Monitor Session Log
# Port: ${portPath}
# Started: ${this.sessionStartTime.toISOString()}
# Extension: VS Code Serial Monitor with Python Backend
# ================================================================
`;
            this.currentSessionStream.write(header);

            // Start periodic flush if interval > 0
            if (this.config.flushIntervalSeconds > 0) {
                this.flushIntervalHandle = setInterval(() => {
                    this.flushBuffer();
                }, this.config.flushIntervalSeconds * 1000);
                console.log(`Started flush interval: ${this.config.flushIntervalSeconds}s`);
            }

            // Set session timeout
            this.sessionTimeoutHandle = setTimeout(() => {
                console.log(`Session timeout reached (${this.config.timeoutSeconds}s)`);
                this.endSession();
                vscode?.window?.showInformationMessage(
                    `Serial session timeout reached (${this.config.timeoutSeconds/60} minutes). Session ended.`,
                    'View Sessions'
                ).then((selection: any) => {
                    if (selection === 'View Sessions') {
                        this.showSessionsFolder();
                    }
                });
            }, this.config.timeoutSeconds * 1000);

            console.log(`Started new session: ${sessionFileName}`);
            vscode?.window?.showInformationMessage(
                `Background monitoring started for ${portPath}`, 
                'View Sessions'
            ).then((selection: any) => {
                if (selection === 'View Sessions') {
                    this.showSessionsFolder();
                }
            });

        } catch (error) {
            console.error('Failed to start session:', error);
            vscode?.window?.showErrorMessage(`Failed to start session: ${error}`);
        }
    }

    public endSession(): void {
        try {
            // Stop flush interval
            if (this.flushIntervalHandle) {
                clearInterval(this.flushIntervalHandle);
                this.flushIntervalHandle = null;
            }

            // Flush any remaining buffered data
            this.flushBuffer();

            if (this.sessionTimeoutHandle) {
                clearTimeout(this.sessionTimeoutHandle);
                this.sessionTimeoutHandle = null;
            }

            if (this.currentSessionStream) {
                // Write session footer
                const endTime = new Date();
                const duration = this.sessionStartTime ? 
                    Math.round((endTime.getTime() - this.sessionStartTime.getTime()) / 1000) : 0;
                
                const footer = `
# ================================================================
# Session ended: ${endTime.toISOString()}
# Duration: ${duration} seconds (${Math.round(duration/60)} minutes)
# File size: ${this.getFileSize(this.currentSessionFile)} bytes
`;
                this.currentSessionStream.write(footer);
                this.currentSessionStream.end();
                this.currentSessionStream = null;

                console.log(`Ended session. Duration: ${duration}s`);
            }

            this.currentSessionFile = null;
            this.sessionStartTime = null;

        } catch (error) {
            console.error('Error ending session:', error);
        }
    }

    public logData(portPath: string, timestamp: string, data: string): void {
        if (!this.config.enabled || !this.currentSessionStream) {
            return;
        }

        try {
            // Add data to buffer
            const logLine = `[${timestamp}] ${data}\n`;
            
            if (this.config.flushIntervalSeconds === 0) {
                // Flush immediately (interval = 0 means write at end of session only)
                this.dataBuffer.push(logLine);
            } else {
                // Add to buffer for periodic flushing
                this.dataBuffer.push(logLine);
            }

            // Check file size and rotate if necessary
            if (this.currentSessionFile && this.getFileSize(this.currentSessionFile) > this.config.maxSizeBytes) {
                console.log('File size limit reached, rotating session file');
                this.flushBuffer(); // Flush before rotating
                this.startSession(portPath); // This will rotate and create new file
            }

        } catch (error) {
            console.error('Error logging data:', error);
        }
    }

    private flushBuffer(): void {
        if (!this.currentSessionStream || this.dataBuffer.length === 0) {
            return;
        }

        try {
            const bufferedData = this.dataBuffer.join('');
            this.currentSessionStream.write(bufferedData);
            this.dataBuffer = [];
            console.log(`Flushed ${bufferedData.length} bytes to session file`);
        } catch (error) {
            console.error('Error flushing buffer:', error);
        }
    }

    private rotateSessionFiles(): void {
        try {
            const sessionFiles = this.getSessionFiles();
            
            // Sort by session number (descending)
            sessionFiles.sort((a, b) => b.sessionNumber - a.sessionNumber);

            // Remove excess files
            if (sessionFiles.length >= this.config.maxFiles) {
                const filesToRemove = sessionFiles.slice(this.config.maxFiles - 1);
                for (const file of filesToRemove) {
                    try {
                        fs.unlinkSync(file.path);
                        console.log(`Removed old session file: ${path.basename(file.path)}`);
                    } catch (error) {
                        console.error(`Failed to remove file ${file.path}:`, error);
                    }
                }
            }

            // Rotate remaining files
            for (const file of sessionFiles) {
                if (file.sessionNumber < this.config.maxFiles) {
                    const newNumber = file.sessionNumber + 1;
                    const newPath = file.path.replace(`session-${file.sessionNumber}-`, `session-${newNumber}-`);
                    
                    try {
                        fs.renameSync(file.path, newPath);
                        console.log(`Rotated: session-${file.sessionNumber} -> session-${newNumber}`);
                    } catch (error) {
                        console.error(`Failed to rotate file ${file.path}:`, error);
                    }
                }
            }

        } catch (error) {
            console.error('Error rotating session files:', error);
        }
    }

    private getSessionFiles(): SessionFile[] {
        try {
            if (!fs.existsSync(this.sessionDirectory)) {
                return [];
            }

            const files = fs.readdirSync(this.sessionDirectory);
            const sessionFiles: SessionFile[] = [];

            for (const fileName of files) {
                const match = fileName.match(/^session-(\d+)-.+\.log$/);
                if (match) {
                    const sessionNumber = parseInt(match[1], 10);
                    const filePath = path.join(this.sessionDirectory, fileName);
                    const stats = fs.statSync(filePath);
                    
                    sessionFiles.push({
                        path: filePath,
                        sessionNumber,
                        startTime: stats.birthtime,
                        size: stats.size
                    });
                }
            }

            return sessionFiles;
        } catch (error) {
            console.error('Error getting session files:', error);
            return [];
        }
    }

    private getFileSize(filePath: string | null): number {
        if (!filePath || !fs.existsSync(filePath)) {
            return 0;
        }
        try {
            return fs.statSync(filePath).size;
        } catch {
            return 0;
        }
    }

    public getSessionInfo(): any {
        const sessionFiles = this.getSessionFiles();
        const currentSize = this.getFileSize(this.currentSessionFile);
        const currentDuration = this.sessionStartTime ? 
            Math.round((Date.now() - this.sessionStartTime.getTime()) / 1000) : 0;

        return {
            config: this.config,
            currentSession: {
                active: !!this.currentSessionFile,
                file: this.currentSessionFile ? path.basename(this.currentSessionFile) : null,
                size: currentSize,
                duration: currentDuration,
                startTime: this.sessionStartTime?.toISOString()
            },
            sessionFiles: sessionFiles.map(f => ({
                file: path.basename(f.path),
                sessionNumber: f.sessionNumber,
                size: f.size,
                startTime: f.startTime.toISOString()
            })),
            directory: this.sessionDirectory
        };
    }

    public async showSessionsFolder(): Promise<void> {
        try {
            const uri = vscode?.Uri?.file(this.sessionDirectory);
            await vscode?.commands?.executeCommand('revealFileInOS', uri);
        } catch (error) {
            console.error('Failed to show sessions folder:', error);
            vscode?.window?.showErrorMessage(`Failed to open sessions folder: ${error}`);
        }
    }

    public dispose(): void {
        this.endSession();
    }

    // Configuration change handler
    public onConfigurationChanged(): void {
        const oldConfig = { ...this.config };
        this.updateConfig();
        
        // If directory changed, update it
        if (oldConfig.directory !== this.config.directory) {
            this.sessionDirectory = path.join(this.workspaceRoot, this.config.directory);
            this.ensureSessionDirectory();
        }

        // If monitoring was disabled, end current session
        if (oldConfig.enabled && !this.config.enabled) {
            this.endSession();
            vscode?.window?.showInformationMessage('Background monitoring disabled');
        }

        // If monitoring was enabled, show info
        if (!oldConfig.enabled && this.config.enabled) {
            vscode?.window?.showInformationMessage('Background monitoring enabled');
        }
    }
}
