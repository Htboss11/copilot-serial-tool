import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';

export class MCPAutoRegister {
    private extensionPath: string;

    constructor(extensionPath: string) {
        this.extensionPath = extensionPath;
    }

    /**
     * Automatically register the Serial Monitor MCP server with common MCP clients
     */
    public async autoRegister(): Promise<void> {
        try {
            const mcpServerPath = path.join(this.extensionPath, 'dist', 'mcp-server-pure.js');
            
            // Check if MCP server exists
            if (!fs.existsSync(mcpServerPath)) {
                console.log('MCP server not found, skipping auto-registration');
                return;
            }

            const serverConfig = {
                command: 'node',
                args: [mcpServerPath],
                env: {}
            };

            // Try to register with common MCP clients
            await this.registerWithClaudeDev(serverConfig);
            await this.registerWithClaudeDesktop(serverConfig);
            await this.registerWithRooCline(serverConfig);
            await this.registerWithGitHubCopilot(serverConfig);
            
            console.log('✅ MCP server auto-registration attempted');
            
        } catch (error) {
            console.log('MCP auto-registration failed (this is normal if no MCP clients are installed):', error);
        }
    }

    /**
     * Register with Claude Dev extension for VS Code
     */
    private async registerWithClaudeDev(serverConfig: any): Promise<void> {
        const settingsPath = this.getClaudeDevSettingsPath();
        if (!settingsPath) {
            return;
        }

        try {
            await this.updateMCPConfig(settingsPath, serverConfig);
            console.log('✅ Registered with Claude Dev');
        } catch (error) {
            console.log('Claude Dev registration skipped:', error);
        }
    }

    /**
     * Register with Claude Desktop
     */
    private async registerWithClaudeDesktop(serverConfig: any): Promise<void> {
        const configPath = this.getClaudeDesktopConfigPath();
        if (!configPath) {
            return;
        }

        try {
            await this.updateMCPConfig(configPath, serverConfig);
            console.log('✅ Registered with Claude Desktop');
        } catch (error) {
            console.log('Claude Desktop registration skipped:', error);
        }
    }

    /**
     * Register with GitHub Copilot via VS Code settings
     */
    private async registerWithGitHubCopilot(serverConfig: any): Promise<void> {
        try {
            console.log('🔍 Attempting GitHub Copilot registration...');
            const settingsPath = this.getVSCodeSettingsPath();
            console.log('📁 Settings path:', settingsPath);
            
            if (!settingsPath) {
                console.log('❌ Could not find VS Code settings path');
                return;
            }

            // Read existing settings
            let settings: any = {};
            if (fs.existsSync(settingsPath)) {
                console.log('📖 Reading existing settings...');
                const content = fs.readFileSync(settingsPath, 'utf8');
                try {
                    settings = JSON.parse(content);
                    console.log('✅ Parsed existing settings');
                } catch (error) {
                    console.log('⚠️ Invalid JSON in VS Code settings, creating new config');
                    settings = {};
                }
            } else {
                console.log('📝 Settings file does not exist, will create new one');
            }

            // Add MCP server configuration for GitHub Copilot
            if (!settings['chat.mcp.servers']) {
                console.log('➕ Creating chat.mcp.servers section');
                settings['chat.mcp.servers'] = {};
            }
            settings['chat.mcp.servers']['serial-monitor'] = serverConfig;
            console.log('✅ Added to chat.mcp.servers');

            // Also add to serverSampling for GitHub Copilot UI visibility
            if (!settings['chat.mcp.serverSampling']) {
                console.log('➕ Creating chat.mcp.serverSampling section');
                settings['chat.mcp.serverSampling'] = {};
            }
            settings['chat.mcp.serverSampling']['serial-monitor'] = serverConfig;
            console.log('✅ Added to chat.mcp.serverSampling');

            // Write back to settings
            console.log('💾 Writing settings back to file...');
            fs.writeFileSync(settingsPath, JSON.stringify(settings, null, 4));
            console.log('✅ Successfully registered with GitHub Copilot!');
            
            // Show user notification
            vscode.window.showInformationMessage(
                'Serial Monitor MCP server registered with GitHub Copilot!',
                'Open Settings'
            ).then(selection => {
                if (selection === 'Open Settings') {
                    vscode.commands.executeCommand('workbench.action.openSettings', 'chat.mcp.serverSampling');
                }
            });
            
        } catch (error) {
            console.error('❌ Failed to register with GitHub Copilot:', error);
            vscode.window.showWarningMessage(
                `Failed to auto-register MCP server: ${error}. You can manually register it in settings.`
            );
        }
    }

    /**
     * Register with Roo Cline extension for VS Code
     */
    private async registerWithRooCline(serverConfig: any): Promise<void> {
        const paths = [
            this.getRooCliineSettingsPath(),
            this.getRooCodeNightlySettingsPath()
        ];
        
        for (const settingsPath of paths) {
            if (settingsPath) {
                try {
                    await this.updateMCPConfig(settingsPath, serverConfig);
                    console.log('✅ Registered with Roo Cline:', settingsPath);
                } catch (error) {
                    console.log('Failed to register with Roo Cline:', error);
                }
            }
        }
    }

    /**
     * Update MCP configuration file
     */
    private async updateMCPConfig(configPath: string, serverConfig: any): Promise<void> {
        // Ensure directory exists
        const dir = path.dirname(configPath);
        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
        }

        let config: any = {};
        
        // Read existing config if it exists
        if (fs.existsSync(configPath)) {
            try {
                const content = fs.readFileSync(configPath, 'utf8');
                config = JSON.parse(content);
            } catch (error) {
                console.log('Invalid JSON in config file, creating new one');
                config = {};
            }
        }

        // Ensure mcpServers object exists
        if (!config.mcpServers) {
            config.mcpServers = {};
        }

        // Add or update our server
        config.mcpServers['serial-monitor'] = serverConfig;

        // Write back to file
        fs.writeFileSync(configPath, JSON.stringify(config, null, 2));
    }

    /**
     * Get Claude Dev settings path based on OS
     */
    private getClaudeDevSettingsPath(): string | null {
        const userDataDir = this.getVSCodeUserDataDir();
        if (!userDataDir) {
            return null;
        }

        return path.join(
            userDataDir,
            'globalStorage',
            'saoudrizwan.claude-dev',
            'settings',
            'cline_mcp_settings.json'
        );
    }

    /**
     * Get Roo Cline settings path
     */
    private getRooCliineSettingsPath(): string | null {
        const userDataDir = this.getVSCodeUserDataDir();
        if (!userDataDir) {
            return null;
        }

        return path.join(
            userDataDir,
            'globalStorage',
            'rooveterinaryinc.roo-cline',
            'settings',
            'mcp_settings.json'
        );
    }

    /**
     * Get Roo Code Nightly settings path
     */
    private getRooCodeNightlySettingsPath(): string | null {
        const userDataDir = this.getVSCodeUserDataDir();
        if (!userDataDir) {
            return null;
        }

        return path.join(
            userDataDir,
            'globalStorage',
            'rooveterinaryinc.roo-code-nightly',
            'settings',
            'mcp_settings.json'
        );
    }

    /**
     * Get Claude Desktop config path based on OS
     */
    private getClaudeDesktopConfigPath(): string | null {
        const homeDir = os.homedir();
        
        switch (process.platform) {
            case 'win32':
                return path.join(process.env.APPDATA || homeDir, 'Claude', 'claude_desktop_config.json');
            case 'darwin':
                return path.join(homeDir, 'Library', 'Application Support', 'Claude', 'claude_desktop_config.json');
            case 'linux':
                return path.join(homeDir, '.config', 'claude', 'claude_desktop_config.json');
            default:
                return null;
        }
    }

    /**
     * Get VS Code settings.json path
     */
    private getVSCodeSettingsPath(): string | null {
        const userDataDir = this.getVSCodeUserDataDir();
        if (!userDataDir) {
            return null;
        }
        return path.join(userDataDir, 'settings.json');
    }

    /**
     * Get VS Code user data directory
     */
    private getVSCodeUserDataDir(): string | null {
        const homeDir = os.homedir();
        
        switch (process.platform) {
            case 'win32':
                return path.join(process.env.APPDATA || homeDir, 'Code', 'User');
            case 'darwin':
                return path.join(homeDir, 'Library', 'Application Support', 'Code', 'User');
            case 'linux':
                return path.join(homeDir, '.config', 'Code', 'User');
            default:
                return null;
        }
    }

    /**
     * Show user notification about MCP registration
     */
    public async showRegistrationNotification(): Promise<void> {
        const action = await vscode.window.showInformationMessage(
            'Serial Monitor can integrate with AI agents via MCP. Register automatically?',
            'Yes', 'No', 'Show Setup Guide'
        );

        if (action === 'Yes') {
            await this.autoRegister();
            vscode.window.showInformationMessage('✅ MCP server registered! Restart your AI client to see serial tools.');
        } else if (action === 'Show Setup Guide') {
            // Open the MCP setup guide
            const setupGuide = vscode.Uri.file(path.join(this.extensionPath, 'MCP_SETUP.md'));
            await vscode.commands.executeCommand('markdown.showPreview', setupGuide);
        }
    }
}