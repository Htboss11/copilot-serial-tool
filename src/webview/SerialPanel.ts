import * as vscode from 'vscode';
import { SerialManager } from '../serialManager';

export class SerialPanel {
    public static currentPanel: SerialPanel | undefined;
    private readonly _panel: vscode.WebviewPanel;
    private readonly _extensionUri: vscode.Uri;
    private _disposables: vscode.Disposable[] = [];
    private serialManager: SerialManager;
    private currentPort: string | null = null;

    public static createOrShow(extensionUri: vscode.Uri, serialManager: SerialManager) {
        const column = vscode.window.activeTextEditor
            ? vscode.window.activeTextEditor.viewColumn
            : undefined;

        // If we already have a panel, show it.
        if (SerialPanel.currentPanel) {
            SerialPanel.currentPanel._panel.reveal(column);
            return;
        }

        // Otherwise, create a new panel.
        const panel = vscode.window.createWebviewPanel(
            'serialMonitor',
            'Serial Monitor',
            column || vscode.ViewColumn.One,
            {
                enableScripts: true,
                retainContextWhenHidden: true
            }
        );

        SerialPanel.currentPanel = new SerialPanel(panel, extensionUri, serialManager);
    }

    private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri, serialManager: SerialManager) {
        this._panel = panel;
        this._extensionUri = extensionUri;
        this.serialManager = serialManager;

        // Set the webview's initial html content
        this._update();

        // Listen for when the panel is disposed
        // This happens when the user closes the panel or when the panel is closed programmatically
        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);

        // Handle messages from the webview
        this._panel.webview.onDidReceiveMessage(
            message => {
                switch (message.command) {
                    case 'connect':
                        this._handleConnect(message.port, message.baudRate);
                        return;
                    case 'disconnect':
                        this._handleDisconnect();
                        return;
                    case 'send':
                        this._handleSend(message.data);
                        return;
                    case 'clear':
                        this._handleClear();
                        return;
                    case 'listPorts':
                        this._handleListPorts();
                        return;
                    case 'detectPico':
                        this._handleDetectPico();
                        return;
                }
            },
            null,
            this._disposables
        );
    }

    private async _handleConnect(port: string, baudRate: number) {
        try {
            await this.serialManager.connect(port, baudRate);
            this.currentPort = port;
            
            // Set up data listener
            this.serialManager.onData(port, (data: string) => {
                this._panel.webview.postMessage({
                    command: 'data',
                    data: `[${new Date().toLocaleTimeString()}] ${data}`
                });
            });

            this._panel.webview.postMessage({
                command: 'connected',
                port: port,
                baudRate: baudRate
            });
        } catch (error) {
            this._panel.webview.postMessage({
                command: 'error',
                message: `Failed to connect: ${error}`
            });
        }
    }

    private async _handleDisconnect() {
        if (this.currentPort) {
            try {
                await this.serialManager.disconnect(this.currentPort);
                this._panel.webview.postMessage({
                    command: 'disconnected'
                });
                this.currentPort = null;
            } catch (error) {
                this._panel.webview.postMessage({
                    command: 'error',
                    message: `Failed to disconnect: ${error}`
                });
            }
        }
    }

    private async _handleSend(data: string) {
        if (this.currentPort) {
            try {
                await this.serialManager.send(this.currentPort, data);
                this._panel.webview.postMessage({
                    command: 'sent',
                    data: data
                });
            } catch (error) {
                this._panel.webview.postMessage({
                    command: 'error',
                    message: `Failed to send: ${error}`
                });
            }
        } else {
            this._panel.webview.postMessage({
                command: 'error',
                message: 'Not connected to any port'
            });
        }
    }

    private _handleClear() {
        this._panel.webview.postMessage({
            command: 'clear'
        });
    }

    private async _handleListPorts() {
        try {
            const ports = await this.serialManager.listPorts();
            this._panel.webview.postMessage({
                command: 'ports',
                ports: ports
            });
        } catch (error) {
            this._panel.webview.postMessage({
                command: 'error',
                message: `Failed to list ports: ${error}`
            });
        }
    }

    private async _handleDetectPico() {
        try {
            const port = await this.serialManager.detectPico();
            this._panel.webview.postMessage({
                command: 'picoDetected',
                port: port
            });
        } catch (error) {
            this._panel.webview.postMessage({
                command: 'error',
                message: `Failed to detect Pico: ${error}`
            });
        }
    }

    public dispose() {
        SerialPanel.currentPanel = undefined;

        // Clean up our resources
        this._panel.dispose();

        while (this._disposables.length) {
            const x = this._disposables.pop();
            if (x) {
                x.dispose();
            }
        }
    }

    private _update() {
        const webview = this._panel.webview;
        this._panel.webview.html = this._getHtmlForWebview(webview);
    }

    private _getHtmlForWebview(webview: vscode.Webview) {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Serial Monitor</title>
    <style>
        body {
            font-family: var(--vscode-font-family);
            color: var(--vscode-foreground);
            background-color: var(--vscode-editor-background);
            margin: 0;
            padding: 20px;
        }
        .header {
            display: flex;
            gap: 10px;
            align-items: center;
            margin-bottom: 20px;
            padding: 10px;
            background-color: var(--vscode-editor-inactiveSelectionBackground);
            border-radius: 4px;
        }
        .controls {
            display: flex;
            gap: 10px;
            align-items: center;
            flex-wrap: wrap;
        }
        button {
            background-color: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border: none;
            padding: 6px 12px;
            border-radius: 3px;
            cursor: pointer;
        }
        button:hover {
            background-color: var(--vscode-button-hoverBackground);
        }
        button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        select, input {
            background-color: var(--vscode-input-background);
            color: var(--vscode-input-foreground);
            border: 1px solid var(--vscode-input-border);
            padding: 4px 8px;
            border-radius: 3px;
        }
        .output {
            height: 400px;
            background-color: var(--vscode-editor-background);
            border: 1px solid var(--vscode-input-border);
            padding: 10px;
            overflow-y: auto;
            font-family: var(--vscode-editor-font-family);
            font-size: var(--vscode-editor-font-size);
            white-space: pre-wrap;
            border-radius: 4px;
        }
        .input-section {
            margin-top: 10px;
            display: flex;
            gap: 10px;
            align-items: center;
        }
        .input-field {
            flex: 1;
        }
        .status {
            padding: 10px;
            margin-top: 10px;
            border-radius: 4px;
            font-weight: bold;
        }
        .status.connected {
            background-color: var(--vscode-testing-iconPassed);
            color: var(--vscode-button-foreground);
        }
        .status.disconnected {
            background-color: var(--vscode-testing-iconFailed);
            color: var(--vscode-button-foreground);
        }
        .error {
            color: var(--vscode-errorForeground);
        }
        .data-line {
            margin: 2px 0;
        }
        .data-line.error {
            color: var(--vscode-errorForeground);
        }
        .data-line.success {
            color: var(--vscode-testing-iconPassed);
        }
    </style>
</head>
<body>
    <div class="header">
        <h2>Serial Monitor</h2>
        <div class="controls">
            <select id="portSelect">
                <option value="">Select Port...</option>
            </select>
            <input type="number" id="baudRate" value="115200" placeholder="Baud Rate" style="width: 80px;">
            <button id="refreshPorts">Refresh</button>
            <button id="detectPico">Detect Pico</button>
            <button id="connectBtn">Connect</button>
            <button id="disconnectBtn" disabled>Disconnect</button>
            <button id="clearBtn">Clear</button>
        </div>
    </div>

    <div id="status" class="status disconnected">Disconnected</div>

    <div id="output" class="output"></div>

    <div class="input-section">
        <input type="text" id="sendInput" class="input-field" placeholder="Type command to send..." disabled>
        <button id="sendBtn" disabled>Send</button>
    </div>

    <script>
        const vscode = acquireVsCodeApi();
        
        const portSelect = document.getElementById('portSelect');
        const baudRateInput = document.getElementById('baudRate');
        const connectBtn = document.getElementById('connectBtn');
        const disconnectBtn = document.getElementById('disconnectBtn');
        const refreshBtn = document.getElementById('refreshPorts');
        const detectPicoBtn = document.getElementById('detectPico');
        const clearBtn = document.getElementById('clearBtn');
        const sendInput = document.getElementById('sendInput');
        const sendBtn = document.getElementById('sendBtn');
        const output = document.getElementById('output');
        const status = document.getElementById('status');

        let isConnected = false;

        // Event listeners
        connectBtn.addEventListener('click', () => {
            const port = portSelect.value;
            const baudRate = parseInt(baudRateInput.value) || 115200;
            if (port) {
                vscode.postMessage({
                    command: 'connect',
                    port: port,
                    baudRate: baudRate
                });
            }
        });

        disconnectBtn.addEventListener('click', () => {
            vscode.postMessage({ command: 'disconnect' });
        });

        refreshBtn.addEventListener('click', () => {
            vscode.postMessage({ command: 'listPorts' });
        });

        detectPicoBtn.addEventListener('click', () => {
            vscode.postMessage({ command: 'detectPico' });
        });

        clearBtn.addEventListener('click', () => {
            output.textContent = '';
        });

        sendBtn.addEventListener('click', () => {
            const data = sendInput.value;
            if (data) {
                vscode.postMessage({
                    command: 'send',
                    data: data + '\\n'
                });
                sendInput.value = '';
            }
        });

        sendInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendBtn.click();
            }
        });

        // Handle messages from extension
        window.addEventListener('message', event => {
            const message = event.data;

            switch (message.command) {
                case 'connected':
                    isConnected = true;
                    updateUI();
                    status.textContent = \`Connected to \${message.port} at \${message.baudRate} baud\`;
                    status.className = 'status connected';
                    addToOutput(\`Connected to \${message.port}\`, 'success');
                    break;

                case 'disconnected':
                    isConnected = false;
                    updateUI();
                    status.textContent = 'Disconnected';
                    status.className = 'status disconnected';
                    addToOutput('Disconnected', 'error');
                    break;

                case 'data':
                    addToOutput(message.data);
                    break;

                case 'sent':
                    addToOutput(\`>> \${message.data}\`, 'success');
                    break;

                case 'error':
                    addToOutput(\`ERROR: \${message.message}\`, 'error');
                    break;

                case 'ports':
                    updatePortList(message.ports);
                    break;

                case 'picoDetected':
                    if (message.port) {
                        portSelect.value = message.port;
                        addToOutput(\`Pico detected on \${message.port}\`, 'success');
                    } else {
                        addToOutput('No Pico devices found', 'error');
                    }
                    break;
            }
        });

        function updateUI() {
            connectBtn.disabled = isConnected;
            disconnectBtn.disabled = !isConnected;
            sendInput.disabled = !isConnected;
            sendBtn.disabled = !isConnected;
            portSelect.disabled = isConnected;
            baudRateInput.disabled = isConnected;
        }

        function updatePortList(ports) {
            portSelect.innerHTML = '<option value="">Select Port...</option>';
            ports.forEach(port => {
                const option = document.createElement('option');
                option.value = port.path;
                option.textContent = \`\${port.path}\${port.manufacturer ? \` (\${port.manufacturer})\` : ''}\`;
                portSelect.appendChild(option);
            });
        }

        function addToOutput(text, className = '') {
            const div = document.createElement('div');
            div.className = \`data-line \${className}\`;
            div.textContent = text;
            output.appendChild(div);
            output.scrollTop = output.scrollHeight;
        }

        // Load ports on startup
        vscode.postMessage({ command: 'listPorts' });
    </script>
</body>
</html>`;
    }
}