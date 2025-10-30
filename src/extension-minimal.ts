import * as vscode from 'vscode';

export function activate(context: vscode.ExtensionContext) {
    console.log('🔥 MINIMAL Serial Monitor extension is now active!');
    
    // Register a simple test command
    const disposable = vscode.commands.registerCommand('serial-monitor.open', () => {
        vscode.window.showInformationMessage('🎉 Serial Monitor command works!');
        console.log('✅ Serial Monitor command executed successfully');
    });

    context.subscriptions.push(disposable);
    console.log('✅ Command registered: serial-monitor.open');
}

export function deactivate() {
    console.log('Serial Monitor extension deactivated');
}