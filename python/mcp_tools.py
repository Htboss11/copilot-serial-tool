#!/usr/bin/env python3
"""
MCP Tools for VS Code Serial Monitor
Simple command-line interface for AI agent integration
"""

import json
import sys
import argparse
import subprocess
import time
import os
from pathlib import Path

class SerialMCPTools:
    def __init__(self):
        # Find the extension path
        self.extension_path = Path(__file__).parent.parent
        self.serial_script = self.extension_path / "python" / "serial_monitor.py"
        
    def detect_pico(self):
        """Detect Raspberry Pi Pico on serial ports"""
        try:
            result = subprocess.run([
                'python', str(self.serial_script), 'detect-pico'
            ], capture_output=True, text=True, check=True)
            
            data = json.loads(result.stdout)
            return {
                "success": True,
                "pico_port": data.get("pico_port"),
                "message": f"Pico detected on {data.get('pico_port')}" if data.get('pico_port') else "No Pico detected"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def list_ports(self):
        """List all available serial ports"""
        try:
            result = subprocess.run([
                'python', str(self.serial_script), 'list'
            ], capture_output=True, text=True, check=True)
            
            ports = json.loads(result.stdout)
            return {
                "success": True,
                "ports": ports,
                "count": len(ports)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def send_command(self, port, command):
        """Send a command to the serial device"""
        try:
            result = subprocess.run([
                'python', str(self.serial_script), 'send',
                '--port', port,
                '--data', command
            ], capture_output=True, text=True, check=True)
            
            response = json.loads(result.stdout)
            return {
                "success": response.get("success", False),
                "message": response.get("message", ""),
                "port": port,
                "command": command
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def read_data_stream(self, port, duration_seconds=3):
        """Read data from serial port for a specified duration"""
        try:
            # Start the connection process
            process = subprocess.Popen([
                'python', str(self.serial_script), 'connect',
                '--port', port,
                '--baud', '115200'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # Read data for the specified duration
            data_lines = []
            start_time = time.time()
            
            while time.time() - start_time < duration_seconds:
                try:
                    line = process.stdout.readline()
                    if line:
                        try:
                            parsed = json.loads(line.strip())
                            if parsed.get("type") == "data":
                                data_lines.append({
                                    "timestamp": parsed.get("timestamp"),
                                    "data": parsed.get("data")
                                })
                        except json.JSONDecodeError:
                            # Handle non-JSON output
                            data_lines.append({
                                "timestamp": time.time(),
                                "data": line.strip()
                            })
                except:
                    break
            
            # Terminate the process
            process.terminate()
            process.wait(timeout=2)
            
            return {
                "success": True,
                "port": port,
                "duration": duration_seconds,
                "lines_captured": len(data_lines),
                "data": data_lines
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def interactive_session(self, port, duration_seconds=10):
        """Start an interactive session with real-time monitoring"""
        try:
            print(f"🔌 Starting interactive session with {port} for {duration_seconds} seconds...")
            print("📡 Real-time data stream:")
            print("-" * 50)
            
            # Start the connection process
            process = subprocess.Popen([
                'python', str(self.serial_script), 'connect',
                '--port', port,
                '--baud', '115200'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            data_count = 0
            start_time = time.time()
            
            while time.time() - start_time < duration_seconds:
                try:
                    line = process.stdout.readline()
                    if line:
                        try:
                            parsed = json.loads(line.strip())
                            if parsed.get("type") == "data":
                                timestamp = parsed.get("timestamp", "").split("T")[1][:8]  # HH:MM:SS
                                data = parsed.get("data", "")
                                print(f"[{timestamp}] {data}")
                                data_count += 1
                        except json.JSONDecodeError:
                            print(f"[RAW] {line.strip()}")
                            data_count += 1
                except:
                    break
            
            # Terminate the process
            process.terminate()
            process.wait(timeout=2)
            
            print("-" * 50)
            print(f"✅ Session completed: {data_count} data points captured")
            
            return {
                "success": True,
                "port": port,
                "duration": duration_seconds,
                "data_points": data_count
            }
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return {"success": False, "error": str(e)}

def main():
    parser = argparse.ArgumentParser(description='Serial Monitor MCP Tools')
    parser.add_argument('command', choices=[
        'detect-pico', 'list-ports', 'send', 'read-stream', 'interactive'
    ])
    parser.add_argument('--port', help='Serial port (e.g., COM9)')
    parser.add_argument('--command', help='Command to send')
    parser.add_argument('--duration', type=int, default=3, help='Duration in seconds')
    
    args = parser.parse_args()
    
    tools = SerialMCPTools()
    result = None
    
    if args.command == 'detect-pico':
        result = tools.detect_pico()
    elif args.command == 'list-ports':
        result = tools.list_ports()
    elif args.command == 'send':
        if not args.port or not args.command:
            result = {"success": False, "error": "--port and --command required for send"}
        else:
            result = tools.send_command(args.port, args.command)
    elif args.command == 'read-stream':
        if not args.port:
            result = {"success": False, "error": "--port required for read-stream"}
        else:
            result = tools.read_data_stream(args.port, args.duration)
    elif args.command == 'interactive':
        if not args.port:
            # Auto-detect Pico
            detect_result = tools.detect_pico()
            if detect_result.get("success") and detect_result.get("pico_port"):
                args.port = detect_result["pico_port"]
                print(f"🔍 Auto-detected Pico on {args.port}")
            else:
                result = {"success": False, "error": "No Pico detected and no --port specified"}
        if not result:  # Only run interactive if no error
            result = tools.interactive_session(args.port, args.duration)
    
    # Output result as JSON (except for interactive mode which prints directly)
    if args.command != 'interactive' and result:
        print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()