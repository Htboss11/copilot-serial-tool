#!/usr/bin/env python3
"""
Python Serial Monitor for VS Code Extension
Uses pyserial for reliable cross-platform serial communication
"""

import serial
import serial.tools.list_ports
import threading
import time
import json
import sys
import argparse
from datetime import datetime
import os

class SerialMonitor:
    def __init__(self):
        self.connections = {}
        self.running = {}
        self.output_callbacks = {}
        
        # TEMP DEBUG: Always write a marker file to verify __init__ runs
        try:
            marker_path = os.path.join(os.path.dirname(__file__), '_init_marker.txt')
            with open(marker_path, 'w') as f:
                f.write(f"Init ran at {datetime.now().isoformat()}\n")
                f.write(f"DEBUG env: {os.environ.get('SERIAL_MONITOR_DEBUG')}\n")
                f.write(f"DEBUG_PATH env: {os.environ.get('SERIAL_MONITOR_DEBUG_PATH')}\n")
        except Exception as e:
            pass  # Silent fail
        
        # Debugging: if SERIAL_MONITOR_DEBUG=1 set, log raw reads to a debug file
        self.debug = os.environ.get('SERIAL_MONITOR_DEBUG') == '1'
        if self.debug:
            try:
                # Use SERIAL_MONITOR_DEBUG_PATH if set, else default to script dir
                debug_path = os.environ.get('SERIAL_MONITOR_DEBUG_PATH')
                if debug_path:
                    self.debug_file = debug_path
                else:
                    self.debug_file = os.path.join(os.path.dirname(__file__), 'serial_debug.log')
                # create/clear existing file
                with open(self.debug_file, 'w') as f:
                    f.write(f"Serial debug started: {datetime.now().isoformat()}\n")
            except Exception:
                self.debug = False
        
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
    
    def detect_pico(self):
        """Auto-detect Raspberry Pi Pico devices"""
        for port in serial.tools.list_ports.comports():
            # Pico USB VID:PID is typically 2E8A:0005 or similar
            if (port.vid == 0x2E8A or 
                (port.manufacturer and 'raspberry' in port.manufacturer.lower()) or
                (port.description and 'pico' in port.description.lower())):
                return port.device
        return None
    
    def connect(self, port_path, baud_rate=115200):
        """Connect to a serial port"""
        try:
            if port_path in self.connections:
                return {'success': False, 'error': f'Port {port_path} already connected'}
            
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
            
            # Start reading thread
            thread = threading.Thread(target=self._read_thread, args=(port_path,))
            thread.daemon = True
            thread.start()
            
            return {
                'success': True, 
                'message': f'Connected to {port_path} at {baud_rate} baud'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def read(self, port_path, duration=5):
        """Read data from a serial port for a specified duration"""
        try:
            if port_path not in self.connections:
                return {'success': False, 'error': f'Port {port_path} not connected. Use connect command first.'}
            
            ser = self.connections[port_path]
            ser.timeout = 0.1  # Set read timeout to 100ms
            start_time = time.time()
            lines = []
            
            while (time.time() - start_time) < duration:
                try:
                    # Try to read a line - will block for up to timeout duration
                    line = ser.readline()
                    if line:
                        data = line.decode('utf-8', errors='ignore').strip()
                        if data:
                            lines.append({
                                'timestamp': datetime.now().isoformat(),
                                'data': data
                            })
                except serial.SerialException:
                    break
                except Exception:
                    # Ignore other read errors and continue
                    continue
            
            return {
                'success': True,
                'port': port_path,
                'duration': duration,
                'lines_read': len(lines),
                'data': lines
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def disconnect(self, port_path):
        """Disconnect from a serial port"""
        try:
            if port_path not in self.connections:
                return {'success': False, 'error': f'Port {port_path} not connected'}
            
            self.running[port_path] = False
            time.sleep(0.1)  # Give read thread time to stop
            
            self.connections[port_path].close()
            del self.connections[port_path]
            del self.running[port_path]
            
            return {'success': True, 'message': f'Disconnected from {port_path}'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def send(self, port_path, data):
        """Send data to a serial port"""
        try:
            if port_path not in self.connections:
                return {'success': False, 'error': f'Port {port_path} not connected'}
            
            ser = self.connections[port_path]
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            ser.write(data)
            ser.flush()
            
            return {'success': True, 'message': f'Sent {len(data)} bytes to {port_path}'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _read_thread(self, port_path):
        """Background thread to read from serial port"""
        ser = self.connections[port_path]
        ser.timeout = 0.1  # Set read timeout to 100ms
        
        while self.running.get(port_path, False):
            try:
                # Try to read a line - will block for up to timeout duration
                line = ser.readline()
                # Debug: always log raw read (even empty) when enabled
                if getattr(self, 'debug', False):
                    try:
                        with open(self.debug_file, 'a') as df:
                            df.write(f"{datetime.now().isoformat()} | raw_len={len(line)} | raw={repr(line)}\n")
                    except Exception:
                        pass
                if line:
                    data = line.decode('utf-8', errors='ignore').strip()
                    if data:
                        timestamp = datetime.now().isoformat()
                        output = {
                            'type': 'data',
                            'port': port_path,
                            'timestamp': timestamp,
                            'data': data
                        }
                        print(json.dumps(output), flush=True)
                        
            except serial.SerialException as e:
                error_output = {
                    'type': 'error',
                    'port': port_path,
                    'timestamp': datetime.now().isoformat(),
                    'error': f'Serial exception: {str(e)}'
                }
                print(json.dumps(error_output), flush=True)
                break
            except Exception as e:
                # Log other exceptions but continue
                error_output = {
                    'type': 'error',
                    'port': port_path,
                    'timestamp': datetime.now().isoformat(),
                    'error': f'Read error: {str(e)}'
                }
                print(json.dumps(error_output), flush=True)
    
    def get_status(self, port_path=None):
        """Get connection status"""
        if port_path:
            connected = port_path in self.connections
            return {'port': port_path, 'connected': connected}
        else:
            status = {}
            for port in self.connections:
                status[port] = {'connected': True, 'running': self.running.get(port, False)}
            return status

def main():
    parser = argparse.ArgumentParser(description='Python Serial Monitor')
    parser.add_argument('command', choices=['list', 'detect-pico', 'connect', 'disconnect', 'send', 'read', 'status'])
    parser.add_argument('--port', help='Serial port path')
    parser.add_argument('--baud', type=int, default=115200, help='Baud rate')
    parser.add_argument('--data', help='Data to send')
    parser.add_argument('--duration', type=float, default=5.0, help='Duration in seconds for read command')
    
    args = parser.parse_args()
    
    monitor = SerialMonitor()
    
    try:
        if args.command == 'list':
            result = monitor.list_ports()
        elif args.command == 'detect-pico':
            port = monitor.detect_pico()
            result = {'pico_port': port}
        elif args.command == 'connect':
            if not args.port:
                result = {'success': False, 'error': 'Port required for connect command'}
            else:
                result = monitor.connect(args.port, args.baud)
                # Don't keep running - just connect and return
        elif args.command == 'disconnect':
            if not args.port:
                result = {'success': False, 'error': 'Port required for disconnect command'}
            else:
                result = monitor.disconnect(args.port)
        elif args.command == 'send':
            if not args.port or not args.data:
                result = {'success': False, 'error': 'Port and data required for send command'}
            else:
                result = monitor.send(args.port, args.data)
        elif args.command == 'read':
            if not args.port:
                result = {'success': False, 'error': 'Port required for read command'}
            else:
                result = monitor.read(args.port, args.duration)
        elif args.command == 'status':
            result = monitor.get_status(args.port)
        else:
            result = {'success': False, 'error': 'Unknown command'}
        
        print(json.dumps(result), flush=True)
        
    except Exception as e:
        error_result = {'success': False, 'error': str(e)}
        print(json.dumps(error_result), flush=True)
        sys.exit(1)

if __name__ == '__main__':
    main()