#!/usr/bin/env python3
"""
Persistent Serial Monitor Server
Maintains serial connections across multiple command invocations
Features:
- Automatic reconnection on disconnect
- Circular buffer for last N seconds of data
- Connection state markers in logs
- File logging with session management
"""

import serial
import serial.tools.list_ports
import threading
import time
import json
import sys
import socket
import os
from datetime import datetime
from collections import deque
from pathlib import Path

class CircularBuffer:
    """Thread-safe circular buffer with time-based expiry"""
    def __init__(self, max_seconds=600):
        self.buffer = deque()
        self.max_seconds = max_seconds
        self.lock = threading.Lock()
    
    def add(self, timestamp, data):
        """Add data with timestamp"""
        with self.lock:
            self.buffer.append({'timestamp': timestamp, 'data': data})
            self._cleanup()
    
    def _cleanup(self):
        """Remove entries older than max_seconds"""
        if not self.buffer:
            return
        current_time = datetime.now()
        while self.buffer:
            oldest = self.buffer[0]
            age = (current_time - datetime.fromisoformat(oldest['timestamp'])).total_seconds()
            if age > self.max_seconds:
                self.buffer.popleft()
            else:
                break
    
    def get_all(self):
        """Get all buffered data"""
        with self.lock:
            self._cleanup()
            return list(self.buffer)
    
    def clear(self):
        """Clear buffer"""
        with self.lock:
            self.buffer.clear()

class PersistentSerialServer:
    def __init__(self, port=55556, buffer_seconds=600):
        self.connections = {}
        self.running = {}
        self.buffers = {}
        self.reconnect_threads = {}
        self.log_files = {}  # File handles for logging
        self.log_paths = {}  # File paths for each port
        self.port = port
        self.buffer_seconds = buffer_seconds
        self.server_socket = None
        
        # Create sessions directory
        self.sessions_dir = Path.cwd() / 'serial-sessions'
        self.sessions_dir.mkdir(exist_ok=True)
        
    def _create_log_file(self, port_path, baud_rate):
        """Create a new log file for this port"""
        timestamp = datetime.now().isoformat().replace(':', '-').replace('.', '-')
        safe_port = port_path.replace(':', '').replace('/', '-').replace('\\', '-')
        filename = f"session-mcp-{timestamp}-{safe_port}.log"
        filepath = self.sessions_dir / filename
        
        # Open file for writing
        log_file = open(filepath, 'w', buffering=1)  # Line buffering
        
        # Write header
        header = f"""# Serial Monitor Session Log (MCP Mode)
# Port: {port_path}
# Baud Rate: {baud_rate}
# Started: {datetime.now().isoformat()}
# Server: Persistent Python Serial Server
# ================================================================
"""
        log_file.write(header)
        log_file.flush()
        
        self.log_files[port_path] = log_file
        self.log_paths[port_path] = str(filepath)
        
        print(f"Created log file: {filepath}", file=sys.stderr)
        
    def _log_to_file(self, port_path, timestamp, data):
        """Write a line to the log file"""
        if port_path in self.log_files:
            try:
                log_line = f"[{timestamp}] {data}\n"
                self.log_files[port_path].write(log_line)
                self.log_files[port_path].flush()
            except Exception as e:
                print(f"Error writing to log file: {e}", file=sys.stderr)
                
    def _close_log_file(self, port_path):
        """Close the log file for this port"""
        if port_path in self.log_files:
            try:
                # Write footer
                footer = f"""
# ================================================================
# Session ended: {datetime.now().isoformat()}
# Log file closed
"""
                self.log_files[port_path].write(footer)
                self.log_files[port_path].flush()
                self.log_files[port_path].close()
                
                print(f"Closed log file: {self.log_paths.get(port_path)}", file=sys.stderr)
                
                del self.log_files[port_path]
                if port_path in self.log_paths:
                    del self.log_paths[port_path]
            except Exception as e:
                print(f"Error closing log file: {e}", file=sys.stderr)
        
    def start(self):
        """Start the persistent server"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('localhost', self.port))
        self.server_socket.listen(5)
        
        print(f"Serial Monitor Server started on port {self.port}", file=sys.stderr)
        
        while True:
            try:
                client_socket, address = self.server_socket.accept()
                thread = threading.Thread(target=self.handle_client, args=(client_socket,))
                thread.daemon = True
                thread.start()
            except Exception as e:
                print(f"Server error: {e}", file=sys.stderr)
                break
    
    def handle_client(self, client_socket):
        """Handle a client command"""
        try:
            # Receive command
            data = client_socket.recv(4096).decode('utf-8')
            if not data:
                return
                
            command = json.loads(data)
            method = command.get('method')
            params = command.get('params', {})
            
            # Execute command
            if method == 'list_ports':
                result = self.list_ports()
            elif method == 'connect':
                result = self.connect(params.get('port'), params.get('baudRate', 115200))
            elif method == 'disconnect':
                result = self.disconnect(params.get('port'))
            elif method == 'send':
                result = self.send(params.get('port'), params.get('data'))
            elif method == 'read':
                result = self.read(params.get('port'), params.get('duration', 5))
            elif method == 'get_buffer':
                port = params.get('port')
                seconds = params.get('seconds', None)  # None = all data
                if port not in self.buffers:
                    result = {'success': False, 'error': f'No buffer for port {port}'}
                else:
                    buffer_data = self.buffers[port].get_all()
                    if seconds is not None:
                        # Filter to last N seconds
                        current_time = datetime.now()
                        cutoff_time = current_time.timestamp() - seconds
                        buffer_data = [
                            entry for entry in buffer_data 
                            if datetime.fromisoformat(entry['timestamp']).timestamp() >= cutoff_time
                        ]
                    
                    result = {
                        'success': True,
                        'port': port,
                        'buffer_seconds': self.buffer_seconds,
                        'total_lines': len(buffer_data),
                        'data': buffer_data
                    }
            elif method == 'status':
                result = self.get_status(params.get('port'))
            else:
                result = {'success': False, 'error': f'Unknown method: {method}'}
            
            # Send response
            response = json.dumps(result) + '\n'
            client_socket.sendall(response.encode('utf-8'))
            
        except Exception as e:
            error_response = json.dumps({'success': False, 'error': str(e)}) + '\n'
            client_socket.sendall(error_response.encode('utf-8'))
        finally:
            client_socket.close()
    
    def list_ports(self):
        """List all available serial ports"""
        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append({
                'path': port.device,
                'description': port.description or 'Unknown device',
                'manufacturer': port.manufacturer or '',
                'vid': port.vid,
                'pid': port.pid,
                'serial_number': port.serial_number or ''
            })
        return ports
    
    def connect(self, port_path, baud_rate=115200):
        """Connect to a serial port with auto-reconnect support"""
        try:
            if port_path in self.connections:
                return {
                    'success': True, 
                    'message': f'Port {port_path} already connected',
                    'already_connected': True
                }
            
            # Initialize buffer for this port
            if port_path not in self.buffers:
                self.buffers[port_path] = CircularBuffer(self.buffer_seconds)
            
            # Create log file for this port
            self._create_log_file(port_path, baud_rate)
            
            # Create serial connection
            ser = serial.Serial(
                port=port_path,
                baudrate=baud_rate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False
            )
            
            self.connections[port_path] = ser
            self.running[port_path] = True
            
            # Add connection marker to buffer AND log file
            timestamp = datetime.now().isoformat()
            marker = '=== CONNECTION ESTABLISHED ==='
            self.buffers[port_path].add(timestamp, marker)
            self._log_to_file(port_path, timestamp, marker)
            
            # Start monitoring thread with auto-reconnect
            thread = threading.Thread(target=self._monitor_with_reconnect, args=(port_path, baud_rate))
            thread.daemon = True
            thread.start()
            self.reconnect_threads[port_path] = thread
            
            return {
                'success': True, 
                'message': f'Connected to {port_path} at {baud_rate} baud with auto-reconnect and logging',
                'port': port_path,
                'baudRate': baud_rate,
                'logFile': self.log_paths.get(port_path)
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _monitor_with_reconnect(self, port_path, baud_rate):
        """Monitor serial port with automatic reconnection"""
        reconnect_delay = 2  # seconds
        
        print(f"[MONITOR] Starting monitoring thread for {port_path}", file=sys.stderr)
        
        while self.running.get(port_path, False):
            try:
                ser = self.connections.get(port_path)
                if not ser or not ser.is_open:
                    # Connection lost, attempt reconnect
                    print(f"Connection lost on {port_path}, reconnecting...", file=sys.stderr)
                    timestamp = datetime.now().isoformat()
                    marker = '=== CONNECTION LOST ==='
                    self.buffers[port_path].add(timestamp, marker)
                    self._log_to_file(port_path, timestamp, marker)
                    
                    try:
                        ser = serial.Serial(
                            port=port_path,
                            baudrate=baud_rate,
                            bytesize=serial.EIGHTBITS,
                            parity=serial.PARITY_NONE,
                            stopbits=serial.STOPBITS_ONE,
                            timeout=1,
                            xonxoff=False,
                            rtscts=False,
                            dsrdtr=False
                        )
                        self.connections[port_path] = ser
                        timestamp = datetime.now().isoformat()
                        marker = '=== CONNECTION RESTORED ==='
                        self.buffers[port_path].add(timestamp, marker)
                        self._log_to_file(port_path, timestamp, marker)
                        print(f"Reconnected to {port_path}", file=sys.stderr)
                    except Exception as reconnect_error:
                        print(f"[MONITOR] Reconnect failed: {reconnect_error}", file=sys.stderr)
                        time.sleep(reconnect_delay)
                        continue
                
                # Read data
                if ser.in_waiting > 0:
                    data = ser.readline().decode('utf-8', errors='ignore').strip()
                    if data:
                        timestamp = datetime.now().isoformat()
                        # Add to buffer AND log to file
                        self.buffers[port_path].add(timestamp, data)
                        self._log_to_file(port_path, timestamp, data)
                        print(f"[MONITOR] Captured: {data[:50]}...", file=sys.stderr)
                
                time.sleep(0.01)
                
            except Exception as e:
                print(f"Monitor error on {port_path}: {e}", file=sys.stderr)
                time.sleep(reconnect_delay)
    
    def disconnect(self, port_path):
        """Disconnect from a serial port"""
        try:
            if port_path not in self.connections:
                return {'success': False, 'error': f'Port {port_path} not connected'}
            
            # Stop monitoring
            self.running[port_path] = False
            time.sleep(0.2)  # Give monitor thread time to stop
            
            # Add disconnection marker to buffer AND log file
            if port_path in self.buffers:
                timestamp = datetime.now().isoformat()
                marker = '=== DISCONNECTED BY USER ==='
                self.buffers[port_path].add(timestamp, marker)
                self._log_to_file(port_path, timestamp, marker)
            
            # Close log file
            self._close_log_file(port_path)
            
            # Close connection
            if self.connections[port_path].is_open:
                self.connections[port_path].close()
            del self.connections[port_path]
            del self.running[port_path]
            
            if port_path in self.reconnect_threads:
                del self.reconnect_threads[port_path]
            
            return {'success': True, 'message': f'Disconnected from {port_path}'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def send(self, port_path, data):
        """Send data to a serial port"""
        try:
            if port_path not in self.connections:
                return {'success': False, 'error': f'Port {port_path} not connected. Use connect first.'}
            
            ser = self.connections[port_path]
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            ser.write(data)
            ser.flush()
            
            return {'success': True, 'message': f'Sent {len(data)} bytes to {port_path}'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def read(self, port_path, duration=5):
        """Read data from buffer for a specified duration or get buffered history"""
        try:
            if port_path not in self.connections:
                return {'success': False, 'error': f'Port {port_path} not connected. Use connect first.'}
            
            if port_path not in self.buffers:
                return {'success': False, 'error': f'No buffer for port {port_path}'}
            
            # Get all buffered data first (historical + new)
            all_data = self.buffers[port_path].get_all()
            
            if duration > 0:
                # Wait for additional data
                start_time = time.time()
                initial_count = len(all_data)
                
                while (time.time() - start_time) < duration:
                    time.sleep(0.1)
                    all_data = self.buffers[port_path].get_all()
                
                new_count = len(all_data)
                lines_during_read = new_count - initial_count
            else:
                lines_during_read = len(all_data)
            
            return {
                'success': True,
                'port': port_path,
                'duration': duration,
                'total_lines': len(all_data),
                'lines_during_read': lines_during_read,
                'buffer_seconds': self.buffer_seconds,
                'data': all_data
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_status(self, port_path=None):
        """Get connection status"""
        if port_path:
            connected = port_path in self.connections
            return {
                'port': port_path, 
                'connected': connected,
                'running': self.running.get(port_path, False) if connected else False
            }
        else:
            status = {}
            for port in self.connections:
                status[port] = {
                    'connected': True, 
                    'running': self.running.get(port, False)
                }
            return status

if __name__ == '__main__':
    server = PersistentSerialServer()
    server.start()
