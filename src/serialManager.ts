import { SerialPort } from 'serialport';
import { ReadlineParser } from '@serialport/parser-readline';
import { PortInfo } from '@serialport/bindings-interface';

export interface SerialConnection {
    port: SerialPort;
    parser: ReadlineParser;
    isConnected: boolean;
}

export class SerialManager {
    private connections: Map<string, SerialConnection> = new Map();
    private dataCallbacks: Map<string, (data: string) => void> = new Map();

    async listPorts(): Promise<PortInfo[]> {
        try {
            return await SerialPort.list();
        } catch (error) {
            console.error('Failed to list serial ports:', error);
            return [];
        }
    }

    async detectPico(): Promise<string | null> {
        try {
            const ports = await this.listPorts();
            // Look for Raspberry Pi Pico (VID/PID: 2E8A:0005 or similar)
            const picoPort = ports.find(port => 
                port.vendorId?.toLowerCase() === '2e8a' || 
                port.manufacturer?.toLowerCase().includes('raspberry') ||
                port.productId?.toLowerCase() === '0005'
            );
            return picoPort?.path || null;
        } catch (error) {
            console.error('Failed to detect Pico:', error);
            return null;
        }
    }

    async connect(portPath: string, baudRate: number = 115200): Promise<void> {
        try {
            if (this.connections.has(portPath)) {
                throw new Error(`Port ${portPath} is already connected`);
            }

            const port = new SerialPort({
                path: portPath,
                baudRate: baudRate,
                autoOpen: false
            });

            const parser = port.pipe(new ReadlineParser({ delimiter: '\n' }));

            await new Promise<void>((resolve, reject) => {
                port.open((error) => {
                    if (error) {
                        reject(error);
                    } else {
                        resolve();
                    }
                });
            });

            const connection: SerialConnection = {
                port,
                parser,
                isConnected: true
            };

            this.connections.set(portPath, connection);

            // Set up data callback
            parser.on('data', (data: string) => {
                const callback = this.dataCallbacks.get(portPath);
                if (callback) {
                    callback(data.trim());
                }
            });

            console.log(`Connected to ${portPath} at ${baudRate} baud`);
        } catch (error) {
            console.error(`Failed to connect to ${portPath}:`, error);
            throw error;
        }
    }

    async disconnect(portPath: string): Promise<void> {
        try {
            const connection = this.connections.get(portPath);
            if (!connection) {
                throw new Error(`Port ${portPath} is not connected`);
            }

            await new Promise<void>((resolve, reject) => {
                connection.port.close((error) => {
                    if (error) {
                        reject(error);
                    } else {
                        resolve();
                    }
                });
            });

            this.connections.delete(portPath);
            this.dataCallbacks.delete(portPath);
            console.log(`Disconnected from ${portPath}`);
        } catch (error) {
            console.error(`Failed to disconnect from ${portPath}:`, error);
            throw error;
        }
    }

    async send(portPath: string, data: string): Promise<void> {
        try {
            const connection = this.connections.get(portPath);
            if (!connection || !connection.isConnected) {
                throw new Error(`Port ${portPath} is not connected`);
            }

            await new Promise<void>((resolve, reject) => {
                connection.port.write(data, (error) => {
                    if (error) {
                        reject(error);
                    } else {
                        resolve();
                    }
                });
            });
        } catch (error) {
            console.error(`Failed to send data to ${portPath}:`, error);
            throw error;
        }
    }

    onData(portPath: string, callback: (data: string) => void): void {
        this.dataCallbacks.set(portPath, callback);
    }

    isConnected(portPath: string): boolean {
        const connection = this.connections.get(portPath);
        return connection?.isConnected || false;
    }

    getConnectedPorts(): string[] {
        return Array.from(this.connections.keys()).filter(port => this.isConnected(port));
    }

    async disconnectAll(): Promise<void> {
        const disconnectPromises = Array.from(this.connections.keys()).map(port => 
            this.disconnect(port).catch(error => 
                console.error(`Failed to disconnect ${port}:`, error)
            )
        );
        await Promise.all(disconnectPromises);
    }
}