import { SerialManager } from './serialManager';

export interface WatchConfig {
    port: string;
    watchFor: string[];
    timeoutMs: number;
    bufferLines?: number;
}

export interface WatchStatus {
    status: 'running' | 'complete' | 'timeout' | 'error';
    output: string;
    matchedPattern?: string;
    elapsedMs: number;
    error?: string;
}

export class CircularBuffer {
    private buffer: string[];
    private maxSize: number;
    private current: number = 0;
    private size: number = 0;

    constructor(maxSize: number = 100) {
        this.maxSize = maxSize;
        this.buffer = new Array(maxSize);
    }

    add(item: string): void {
        this.buffer[this.current] = item;
        this.current = (this.current + 1) % this.maxSize;
        if (this.size < this.maxSize) {
            this.size++;
        }
    }

    getAll(): string[] {
        if (this.size === 0) {
            return [];
        }
        
        const result: string[] = [];
        let start = this.size < this.maxSize ? 0 : this.current;
        
        for (let i = 0; i < this.size; i++) {
            result.push(this.buffer[(start + i) % this.maxSize]);
        }
        
        return result;
    }

    clear(): void {
        this.current = 0;
        this.size = 0;
    }
}

export class WatchTask {
    private config: WatchConfig;
    private serialManager: SerialManager;
    private buffer: CircularBuffer;
    private patterns: RegExp[];
    private startTime: number;
    private status: 'running' | 'complete' | 'timeout' | 'error' = 'running';
    private matchedPattern?: string;
    private timeoutHandle?: NodeJS.Timeout;
    private error?: string;

    constructor(config: WatchConfig, serialManager: SerialManager) {
        this.config = config;
        this.serialManager = serialManager;
        this.buffer = new CircularBuffer(config.bufferLines || 100);
        this.patterns = config.watchFor.map(pattern => new RegExp(pattern, 'i'));
        this.startTime = Date.now();
    }

    start(): void {
        // Set up timeout
        if (this.config.timeoutMs > 0) {
            this.timeoutHandle = setTimeout(() => {
                this.status = 'timeout';
            }, this.config.timeoutMs);
        }

        // Set up data listener
        this.serialManager.onData(this.config.port, (data: string) => {
            if (this.status !== 'running') {
                return;
            }

            // Add timestamp to data
            const timestampedData = `[${new Date().toISOString()}] ${data}`;
            this.buffer.add(timestampedData);

            // Check for pattern matches
            for (let i = 0; i < this.patterns.length; i++) {
                if (this.patterns[i].test(data)) {
                    this.matchedPattern = this.config.watchFor[i];
                    this.status = 'complete';
                    this.cleanup();
                    break;
                }
            }
        });
    }

    stop(): void {
        this.status = 'complete';
        this.cleanup();
    }

    getStatus(): WatchStatus {
        return {
            status: this.status,
            output: this.buffer.getAll().join('\n'),
            matchedPattern: this.matchedPattern,
            elapsedMs: Date.now() - this.startTime,
            error: this.error
        };
    }

    private cleanup(): void {
        if (this.timeoutHandle) {
            clearTimeout(this.timeoutHandle);
            this.timeoutHandle = undefined;
        }
    }
}

export class WatchManager {
    private tasks: Map<string, WatchTask> = new Map();
    private serialManager: SerialManager;
    private taskCounter: number = 0;

    constructor(serialManager: SerialManager) {
        this.serialManager = serialManager;
    }

    async startWatch(config: WatchConfig): Promise<string> {
        try {
            // Auto-detect Pico if port is "auto"
            if (config.port === "auto") {
                const detectedPort = await this.serialManager.detectPico();
                if (!detectedPort) {
                    throw new Error("No Raspberry Pi Pico device detected");
                }
                config.port = detectedPort;
            }

            // Ensure port is connected
            if (!this.serialManager.isConnected(config.port)) {
                await this.serialManager.connect(config.port);
            }

            const taskId = `watch-${++this.taskCounter}`;
            const task = new WatchTask(config, this.serialManager);
            
            this.tasks.set(taskId, task);
            task.start();

            return taskId;
        } catch (error) {
            throw new Error(`Failed to start watch: ${error}`);
        }
    }

    checkStatus(taskId: string): WatchStatus | null {
        const task = this.tasks.get(taskId);
        if (!task) {
            return null;
        }
        return task.getStatus();
    }

    cancelWatch(taskId: string): boolean {
        const task = this.tasks.get(taskId);
        if (!task) {
            return false;
        }

        task.stop();
        this.tasks.delete(taskId);
        return true;
    }

    getActiveTasks(): string[] {
        const activeTasks: string[] = [];
        for (const [taskId, task] of this.tasks.entries()) {
            const status = task.getStatus();
            if (status.status === 'running') {
                activeTasks.push(taskId);
            }
        }
        return activeTasks;
    }

    cleanup(): void {
        // Clean up completed tasks (keep last 10 for reference)
        const taskIds = Array.from(this.tasks.keys());
        if (taskIds.length > 10) {
            const toRemove = taskIds.slice(0, taskIds.length - 10);
            for (const taskId of toRemove) {
                const task = this.tasks.get(taskId);
                if (task && task.getStatus().status !== 'running') {
                    this.tasks.delete(taskId);
                }
            }
        }
    }
}