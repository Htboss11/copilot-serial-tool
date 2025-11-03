"""
MCP Tools for Serial Daemon Control
Provides AI-agent-friendly tools for daemon management and data queries
"""
import os
import sys
import json
import time
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any

# Add daemon directory to path for imports
DAEMON_DIR = Path(__file__).parent
sys.path.insert(0, str(DAEMON_DIR))

from daemon_manager import DaemonManager
from db_manager import DatabaseManager
from daemon_commands import DaemonCommands


def find_serial_ports() -> List[Dict[str, Any]]:
    """
    Find all available serial ports with device information
    
    Returns:
        List of port dictionaries with device, description, manufacturer, vid, pid
    """
    try:
        import serial.tools.list_ports
        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append({
                'device': port.device,
                'description': port.description,
                'manufacturer': port.manufacturer or 'Unknown',
                'vid': port.vid,
                'pid': port.pid,
                'serial_number': port.serial_number or 'Unknown'
            })
        return ports
    except Exception as e:
        print(f"Error listing ports: {e}", file=sys.stderr)
        return []


def find_pico_ports() -> List[str]:
    """
    Find all Raspberry Pi Pico devices
    
    Returns:
        List of port device names (e.g., ['COM9', 'COM10'])
    """
    try:
        import serial.tools.list_ports
        pico_ports = []
        for port in serial.tools.list_ports.comports():
            # Raspberry Pi Pico: VID=2E8A (Raspberry Pi), PID=0005 (Pico)
            is_pico = False
            
            if port.vid == 0x2E8A and port.pid == 0x0005:
                is_pico = True
            elif port.manufacturer and 'Raspberry Pi' in port.manufacturer:
                is_pico = True
            elif port.description and ('Pico' in port.description or 'RP2' in port.description):
                is_pico = True
                
            if is_pico:
                pico_ports.append(port.device)
                
        return pico_ports
    except Exception as e:
        print(f"Error finding Pico ports: {e}", file=sys.stderr)
        return []


class DaemonMCPTools:
    """MCP tools for daemon control and data access"""
    
    def __init__(self):
        """Initialize MCP tools"""
        self.daemon_mgr = DaemonManager()
        self.daemon_script = DAEMON_DIR / "serial_daemon.py"
        self.commands = DaemonCommands()  # Command interface
    
    def start_daemon(self, auto_connect: bool = False, port: str = "COM9", baudrate: int = 115200, 
                    max_records: int = 10000, cleanup_interval: int = 60) -> Dict[str, Any]:
        """
        Start serial daemon (IDEMPOTENT)
        Daemon starts without connecting to any port by default
        
        Args:
            auto_connect: If True, automatically connect to port on startup
            port: Serial port to monitor (if auto_connect=True)
            baudrate: Baud rate (if auto_connect=True)
            max_records: Maximum database records to keep (default 10,000)
            cleanup_interval: Seconds between cleanup runs (default 60)
        
        Returns:
            Status dictionary with success/error information
        """
        # Check if already running
        if self.daemon_mgr.check_daemon_health():
            info = self.daemon_mgr.get_daemon_info()
            return {
                'success': True,
                'message': 'Daemon already running',
                'already_running': True,
                'info': info
            }
        
        # Clean up stale files
        self.daemon_mgr.cleanup_stale_files()
        
        # Start daemon as detached background process
        try:
            # Build command args
            cmd_args = [sys.executable, str(self.daemon_script)]
            
            # Add database settings
            cmd_args.extend(['--max-records', str(max_records)])
            cmd_args.extend(['--cleanup-interval', str(cleanup_interval)])
            
            if auto_connect and port:
                cmd_args.extend(['--port', port, '--baudrate', str(baudrate)])
            else:
                cmd_args.append('--no-autoconnect')
            
            # Use subprocess to start daemon
            # IMPORTANT: Don't capture stdout/stderr to avoid pipe blocking
            if sys.platform == 'win32':
                # Windows: use CREATE_NEW_PROCESS_GROUP to detach
                process = subprocess.Popen(
                    cmd_args,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL
                )
            else:
                # Unix: use nohup-style detachment
                process = subprocess.Popen(
                    cmd_args,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True
                )
            
            # Wait for daemon to start (check for PID file)
            for _ in range(50):  # 5 seconds max
                time.sleep(0.1)
                if self.daemon_mgr.check_daemon_health():
                    info = self.daemon_mgr.get_daemon_info()
                    return {
                        'success': True,
                        'message': 'Daemon started successfully',
                        'already_running': False,
                        'info': info
                    }
            
            # Timeout waiting for daemon to start
            return {
                'success': False,
                'message': 'Daemon process started but did not initialize in time',
                'error': 'STARTUP_TIMEOUT'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to start daemon: {e}',
                'error': str(e)
            }
    
    def stop_daemon(self) -> Dict[str, Any]:
        """
        Stop serial daemon (IDEMPOTENT)
        
        Returns:
            Status dictionary
        """
        # Check if running
        pid_data = self.daemon_mgr.read_pid()
        
        if pid_data is None:
            return {
                'success': True,
                'message': 'Daemon not running',
                'was_running': False
            }
        
        pid, timestamp, port, session_id = pid_data
        
        # Check if process exists
        if not self.daemon_mgr.is_process_running(pid):
            # Stale PID file
            self.daemon_mgr.cleanup_stale_files()
            return {
                'success': True,
                'message': 'Daemon not running (stale PID cleaned up)',
                'was_running': False
            }
        
        # Send SIGTERM
        try:
            if sys.platform == 'win32':
                # Windows: use taskkill
                subprocess.run(['taskkill', '/PID', str(pid), '/F'], 
                             capture_output=True, timeout=5)
            else:
                # Unix: use kill
                import signal
                os.kill(pid, signal.SIGTERM)
            
            # Wait for process to exit
            for _ in range(50):  # 5 seconds max
                time.sleep(0.1)
                if not self.daemon_mgr.is_process_running(pid):
                    # Process exited
                    self.daemon_mgr.cleanup_stale_files()
                    return {
                        'success': True,
                        'message': 'Daemon stopped successfully',
                        'was_running': True
                    }
            
            # Process didn't exit, force kill
            if sys.platform == 'win32':
                subprocess.run(['taskkill', '/PID', str(pid), '/F'], 
                             capture_output=True, timeout=5)
            else:
                os.kill(pid, signal.SIGKILL)
            
            time.sleep(0.5)
            self.daemon_mgr.cleanup_stale_files()
            
            return {
                'success': True,
                'message': 'Daemon force-stopped',
                'was_running': True,
                'force_killed': True
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to stop daemon: {e}',
                'error': str(e)
            }
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get daemon status
        
        Returns:
            Status dictionary with daemon info
        """
        info = self.daemon_mgr.get_daemon_info()
        
        if info is None:
            return {
                'running': False,
                'message': 'Daemon not running'
            }
        
        # Get line count from database
        try:
            db_mgr = DatabaseManager(self.daemon_mgr.db_file)
            line_count = db_mgr.get_line_count(info['session_id'])
            db_mgr.close()
            info['lines_captured'] = line_count
        except Exception as e:
            info['lines_captured'] = None
            info['db_error'] = str(e)
        
        return info
    
    def connect_port(self, port: Optional[str] = None, baudrate: int = 115200) -> Dict[str, Any]:
        """
        Connect daemon to a serial port (start monitoring)
        Auto-detects Raspberry Pi Pico if port not specified
        
        Args:
            port: Serial port to monitor (e.g., "COM9"). If None, auto-detect Pico.
            baudrate: Baud rate (default 115200)
        
        Returns:
            Status dictionary
        """
        # Check if daemon is running
        if not self.daemon_mgr.check_daemon_health():
            return {
                'success': False,
                'message': 'Daemon not running. Start daemon first.',
                'error': 'DAEMON_NOT_RUNNING'
            }
        
        # Auto-detect port if not specified
        if port is None:
            pico_ports = find_pico_ports()
            
            if len(pico_ports) == 0:
                return {
                    'success': False,
                    'message': 'No Raspberry Pi Pico detected. Please specify port manually.',
                    'error': 'NO_PICO_FOUND',
                    'available_ports': find_serial_ports()
                }
            elif len(pico_ports) == 1:
                port = pico_ports[0]
                print(f"Auto-detected Raspberry Pi Pico on {port}")
            else:
                return {
                    'success': False,
                    'message': f'Multiple Raspberry Pi Picos detected: {pico_ports}. Please specify port.',
                    'error': 'MULTIPLE_PICOS',
                    'pico_ports': pico_ports
                }
        
        # Send connect command
        return self.commands.send_command('connect', port=port, baudrate=baudrate)
    
    def disconnect_port(self) -> Dict[str, Any]:
        """
        Disconnect daemon from current serial port (stop monitoring)
        Releases port for other tools to use
        
        Returns:
            Status dictionary
        """
        # Check if daemon is running
        if not self.daemon_mgr.check_daemon_health():
            return {
                'success': False,
                'message': 'Daemon not running',
                'error': 'DAEMON_NOT_RUNNING'
            }
        
        # Send disconnect command
        return self.commands.send_command('disconnect')
    
    def send_data(self, data: str) -> Dict[str, Any]:
        """
        Send data to connected serial device
        
        Args:
            data: String data to send to device
        
        Returns:
            Success status and message
        """
        if not self.daemon_mgr.check_daemon_health():
            return {
                'success': False,
                'message': 'Daemon not running',
                'error': 'DAEMON_NOT_RUNNING'
            }
        
        # Send write command
        return self.commands.send_command('write', data=data)
    
    def query_data(self, sql: str, params: Optional[List[Any]] = None) -> Dict[str, Any]:
        """
        Execute SQL query on serial data
        
        Args:
            sql: SQL SELECT statement
            params: Query parameters (optional)
        
        Returns:
            Query results or error
        """
        if params is None:
            params = []
        
        try:
            db_mgr = DatabaseManager(self.daemon_mgr.db_file)
            results = db_mgr.query(sql, tuple(params))
            db_mgr.close()
            
            return {
                'success': True,
                'results': results,
                'count': len(results)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f'Query failed: {e}'
            }
    
    def get_recent(self, seconds: int = 60, port: Optional[str] = None,
                   session_id: Optional[str] = None, limit: int = 1000) -> Dict[str, Any]:
        """
        Get recent data (convenience wrapper)
        
        Args:
            seconds: Number of seconds to look back
            port: Optional port filter
            session_id: Optional session filter
            limit: Max rows
        
        Returns:
            Recent data or error
        """
        try:
            db_mgr = DatabaseManager(self.daemon_mgr.db_file)
            results = db_mgr.get_recent(seconds, port, session_id, limit)
            db_mgr.close()
            
            return {
                'success': True,
                'results': results,
                'count': len(results),
                'seconds': seconds
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f'Query failed: {e}'
            }
    
    def get_tail(self, lines: int = 100, port: Optional[str] = None,
                 session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get last N lines (tail)
        
        Args:
            lines: Number of lines to return
            port: Optional port filter
            session_id: Optional session filter
        
        Returns:
            Last N lines or error
        """
        try:
            db_mgr = DatabaseManager(self.daemon_mgr.db_file)
            results = db_mgr.get_tail(lines, port, session_id)
            db_mgr.close()
            
            return {
                'success': True,
                'results': results,
                'count': len(results),
                'lines_requested': lines
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f'Query failed: {e}'
            }


# MCP Tool Definitions (for registration)
def get_mcp_tools():
    """
    Get MCP tool definitions
    
    Returns:
        List of tool definitions
    """
    return [
        {
            'name': 'serial_daemon_start',
            'description': 'Start serial monitor daemon (idempotent - safe to call if already running)',
            'parameters': {
                'type': 'object',
                'properties': {
                    'port': {
                        'type': 'string',
                        'description': 'Serial port to monitor (e.g., COM9)',
                        'default': 'COM9'
                    },
                    'baudrate': {
                        'type': 'integer',
                        'description': 'Baud rate for serial connection',
                        'default': 115200
                    }
                }
            }
        },
        {
            'name': 'serial_daemon_stop',
            'description': 'Stop serial monitor daemon gracefully (idempotent)',
            'parameters': {
                'type': 'object',
                'properties': {}
            }
        },
        {
            'name': 'serial_daemon_status',
            'description': 'Get daemon status (running, uptime, lines captured, etc.)',
            'parameters': {
                'type': 'object',
                'properties': {}
            }
        },
        {
            'name': 'serial_daemon_connect',
            'description': 'Connect daemon to a serial port and start monitoring. Daemon must be running first.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'port': {
                        'type': 'string',
                        'description': 'Serial port to monitor (e.g., COM9)',
                        'default': 'COM9'
                    },
                    'baudrate': {
                        'type': 'integer',
                        'description': 'Baud rate for serial connection',
                        'default': 115200
                    }
                },
                'required': ['port']
            }
        },
        {
            'name': 'serial_daemon_disconnect',
            'description': 'Disconnect daemon from serial port and stop monitoring. Releases port for other tools. Daemon keeps running.',
            'parameters': {
                'type': 'object',
                'properties': {}
            }
        },
        {
            'name': 'serial_send_data',
            'description': 'Send data/command to connected serial device. Use when you need to send commands, control device, or transmit data to hardware.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'data': {
                        'type': 'string',
                        'description': 'Data string to send to device (newline will be added automatically)'
                    }
                },
                'required': ['data']
            }
        },
        {
            'name': 'serial_query',
            'description': 'Execute SQL query on serial data (SELECT only)',
            'parameters': {
                'type': 'object',
                'properties': {
                    'sql': {
                        'type': 'string',
                        'description': 'SQL SELECT query'
                    },
                    'params': {
                        'type': 'array',
                        'description': 'Query parameters',
                        'items': {},
                        'default': []
                    }
                },
                'required': ['sql']
            }
        },
        {
            'name': 'serial_get_recent',
            'description': 'Get recent serial data from last N seconds',
            'parameters': {
                'type': 'object',
                'properties': {
                    'seconds': {
                        'type': 'integer',
                        'description': 'Number of seconds to look back',
                        'default': 60
                    },
                    'port': {
                        'type': 'string',
                        'description': 'Filter by port (optional)'
                    },
                    'session_id': {
                        'type': 'string',
                        'description': 'Filter by session (optional)'
                    },
                    'limit': {
                        'type': 'integer',
                        'description': 'Maximum rows to return',
                        'default': 1000
                    }
                }
            }
        },
        {
            'name': 'serial_get_tail',
            'description': 'Get last N lines of serial data (like tail command)',
            'parameters': {
                'type': 'object',
                'properties': {
                    'lines': {
                        'type': 'integer',
                        'description': 'Number of lines to return',
                        'default': 100
                    },
                    'port': {
                        'type': 'string',
                        'description': 'Filter by port (optional)'
                    },
                    'session_id': {
                        'type': 'string',
                        'description': 'Filter by session (optional)'
                    }
                }
            }
        }
    ]


# CLI for testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Daemon MCP Tools CLI")
    parser.add_argument('command', choices=['start', 'stop', 'status', 'connect', 'disconnect', 'recent', 'tail'])
    parser.add_argument('--port', default='COM9', help='Serial port (e.g., COM9)')
    parser.add_argument('--baudrate', type=int, default=115200, help='Baud rate (default: 115200)')
    parser.add_argument('--no-autoconnect', action='store_true', help='Start daemon without auto-connecting to port')
    parser.add_argument('--seconds', type=int, default=60, help='Seconds of data to retrieve')
    parser.add_argument('--lines', type=int, default=100, help='Number of lines to retrieve')
    
    args = parser.parse_args()
    
    tools = DaemonMCPTools()
    
    if args.command == 'start':
        auto_connect = not args.no_autoconnect
        result = tools.start_daemon(
            port=args.port if auto_connect else None,
            baudrate=args.baudrate,
            auto_connect=auto_connect
        )
    elif args.command == 'stop':
        result = tools.stop_daemon()
    elif args.command == 'status':
        result = tools.get_status()
    elif args.command == 'connect':
        result = tools.connect_port(args.port, args.baudrate)
    elif args.command == 'disconnect':
        result = tools.disconnect_port()
    elif args.command == 'recent':
        result = tools.get_recent(args.seconds)
    elif args.command == 'tail':
        result = tools.get_tail(args.lines)
    
    print(json.dumps(result, indent=2))
