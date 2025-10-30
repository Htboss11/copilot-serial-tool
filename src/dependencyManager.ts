import { spawn } from 'child_process';
import * as vscode from 'vscode';

export interface DependencyStatus {
    python: boolean;
    pyserial: boolean;
    pythonVersion?: string;
    allSatisfied: boolean;
}

export class DependencyManager {
    private static instance: DependencyManager;

    public static getInstance(): DependencyManager {
        if (!DependencyManager.instance) {
            DependencyManager.instance = new DependencyManager();
        }
        return DependencyManager.instance;
    }

    /**
     * Check all required dependencies
     */
    public async checkDependencies(): Promise<DependencyStatus> {
        const pythonCheck = await this.checkPython();
        let pyserialCheck = false;
        
        if (pythonCheck.available) {
            pyserialCheck = await this.checkPyserial();
        }

        return {
            python: pythonCheck.available,
            pyserial: pyserialCheck,
            pythonVersion: pythonCheck.version,
            allSatisfied: pythonCheck.available && pyserialCheck
        };
    }

    /**
     * Check if Python is available
     */
    private async checkPython(): Promise<{ available: boolean; version?: string }> {
        return new Promise((resolve) => {
            const python = spawn('python', ['--version'], { stdio: ['pipe', 'pipe', 'pipe'] });
            
            let output = '';
            python.stdout.on('data', (data) => {
                output += data.toString();
            });

            python.on('close', (code) => {
                if (code === 0 && output.includes('Python')) {
                    const version = output.trim().replace('Python ', '');
                    resolve({ available: true, version });
                } else {
                    resolve({ available: false });
                }
            });

            python.on('error', () => {
                resolve({ available: false });
            });

            // Timeout after 5 seconds
            setTimeout(() => {
                python.kill();
                resolve({ available: false });
            }, 5000);
        });
    }

    /**
     * Check if pyserial is available
     */
    private async checkPyserial(): Promise<boolean> {
        return new Promise((resolve) => {
            const python = spawn('python', ['-c', 'import serial; print("OK")'], { 
                stdio: ['pipe', 'pipe', 'pipe'] 
            });
            
            let success = false;
            python.stdout.on('data', (data) => {
                if (data.toString().trim() === 'OK') {
                    success = true;
                }
            });

            python.on('close', (code) => {
                resolve(code === 0 && success);
            });

            python.on('error', () => {
                resolve(false);
            });

            // Timeout after 5 seconds
            setTimeout(() => {
                python.kill();
                resolve(false);
            }, 5000);
        });
    }

    /**
     * Install pyserial with user confirmation
     */
    public async installPyserial(): Promise<boolean> {
        return new Promise((resolve) => {
            vscode.window.withProgress({
                location: vscode.ProgressLocation.Notification,
                title: "Installing pyserial...",
                cancellable: false
            }, async (progress) => {
                progress.report({ increment: 0, message: "Running pip install pyserial" });

                const pip = spawn('python', ['-m', 'pip', 'install', 'pyserial==3.5'], {
                    stdio: ['pipe', 'pipe', 'pipe']
                });

                let stdout = '';
                let stderr = '';

                pip.stdout.on('data', (data) => {
                    stdout += data.toString();
                    progress.report({ 
                        increment: 25, 
                        message: "Installing..." 
                    });
                });

                pip.stderr.on('data', (data) => {
                    stderr += data.toString();
                });

                pip.on('close', (code) => {
                    if (code === 0) {
                        progress.report({ increment: 100, message: "Installation complete!" });
                        vscode.window.showInformationMessage('✅ pyserial installed successfully!');
                        resolve(true);
                    } else {
                        console.error('pip install failed:', stderr);
                        vscode.window.showErrorMessage(
                            `Failed to install pyserial: ${stderr.slice(0, 100)}...`
                        );
                        resolve(false);
                    }
                });

                pip.on('error', (error) => {
                    console.error('pip install error:', error);
                    vscode.window.showErrorMessage(
                        `Failed to start pip: ${error.message}`
                    );
                    resolve(false);
                });
            });
        });
    }

    /**
     * Show dependency status notification with install options
     */
    public async showDependencyNotification(status: DependencyStatus): Promise<void> {
        if (status.allSatisfied) {
            // All dependencies satisfied - silent success
            console.log('✅ All dependencies satisfied');
            return;
        }

        if (!status.python) {
            // Python not found - critical error
            const action = await vscode.window.showErrorMessage(
                '🐍 Python is required for Serial Monitor extension',
                {
                    modal: false,
                    detail: 'Python 3.7+ is required for serial communication. Please install Python and restart VS Code.'
                },
                'Download Python',
                'Learn More'
            );

            if (action === 'Download Python') {
                vscode.env.openExternal(vscode.Uri.parse('https://www.python.org/downloads/'));
            } else if (action === 'Learn More') {
                vscode.env.openExternal(vscode.Uri.parse('https://code.visualstudio.com/docs/python/python-tutorial'));
            }
            return;
        }

        if (!status.pyserial) {
            // pyserial not found - offer to install
            const action = await vscode.window.showWarningMessage(
                '📦 pyserial package is required for Serial Monitor',
                {
                    modal: false,
                    detail: 'The pyserial Python package is needed for serial communication. Would you like to install it now?'
                },
                'Install Now',
                'Install Manually',
                'Later'
            );

            if (action === 'Install Now') {
                const success = await this.installPyserial();
                if (success) {
                    // Re-check dependencies after installation
                    const newStatus = await this.checkDependencies();
                    if (newStatus.allSatisfied) {
                        vscode.window.showInformationMessage(
                            '🎉 Serial Monitor is ready to use!',
                            'Open Serial Monitor'
                        ).then(selection => {
                            if (selection === 'Open Serial Monitor') {
                                vscode.commands.executeCommand('serial-monitor.open');
                            }
                        });
                    }
                }
            } else if (action === 'Install Manually') {
                vscode.window.showInformationMessage(
                    'To install manually, run: pip install pyserial',
                    'Copy Command'
                ).then(selection => {
                    if (selection === 'Copy Command') {
                        vscode.env.clipboard.writeText('pip install pyserial');
                        vscode.window.showInformationMessage('Command copied to clipboard!');
                    }
                });
            }
        }
    }

    /**
     * Get a user-friendly status message
     */
    public getStatusMessage(status: DependencyStatus): string {
        if (status.allSatisfied) {
            return `✅ Ready (Python ${status.pythonVersion})`;
        }
        
        if (!status.python) {
            return '❌ Python not found';
        }
        
        if (!status.pyserial) {
            return '⚠️ pyserial not installed';
        }

        return '❌ Dependencies missing';
    }
}