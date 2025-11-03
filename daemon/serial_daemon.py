"""
Serial Monitor Daemon - Main Process
System-wide singleton daemon for serial port monitoring
"""
import os
import sys
import signal
import time
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional

# Import our modules
from daemon_manager import DaemonManager
from db_manager import DatabaseManager
from serial_handler import SerialHandler
from daemon_commands import DaemonCommands


class SerialDaemon:
    """Main daemon process for serial monitoring"""
    
    def __init__(self, max_records: int = 10000, cleanup_interval: int = 60):
        """
        Initialize daemon (does NOT connect to port immediately)
        Use connect_port() to start monitoring a specific port
        
        Args:
            max_records: Maximum database records to keep (default 10,000)
            cleanup_interval: Seconds between cleanup runs (default 60)
        """
        # Initialize managers
        self.daemon_mgr = DaemonManager()
        self.db_mgr: Optional[DatabaseManager] = None
        self.serial_handler: Optional[SerialHandler] = None
        self.command_interface = DaemonCommands()  # Command routing
        
        # Database settings
        self.max_records = max_records
        self.cleanup_interval = cleanup_interval
        
        # Current port info (None until connected)
        self.current_port: Optional[str] = None
        self.current_baudrate: Optional[int] = None
        
        # Session info
        self.session_id = f"session_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        # Running flag
        self.running = False
        self.monitoring = False  # True when actively monitoring a port
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        print(f"Daemon initialized (session: {self.session_id})")
        print(f"Database settings: max_records={max_records:,}, cleanup_interval={cleanup_interval}s")
        print("Use connect_port(port, baudrate) to start monitoring")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals (SIGTERM, SIGINT)"""
        signal_name = "SIGTERM" if signum == signal.SIGTERM else "SIGINT"
        print(f"\nReceived {signal_name}, shutting down gracefully...")
        self.stop()
    
    def start(self) -> bool:
        """
        Start daemon (implements all startup scenarios)
        Does NOT connect to serial port - use connect_port() for that
        
        Returns:
            True if started successfully, False otherwise
        """
        print("=== Starting Serial Monitor Daemon ===")
        
        # SCENARIO 2.3 & 2.4: Clean up stale files from previous crash
        if not self.daemon_mgr.cleanup_stale_files():
            # Daemon already running
            info = self.daemon_mgr.get_daemon_info()
            if info:
                print(f"Daemon already running (PID {info['pid']}, uptime {info['uptime']:.0f}s)")
                return False
        
        # SCENARIO 2.1/2.2: Acquire lock (atomic operation, handles race conditions)
        if not self.daemon_mgr.acquire_lock():
            print("Failed to acquire lock - another daemon may be starting")
            return False
        
        try:
            # Write PID file (no port yet)
            self.daemon_mgr.write_pid("NONE", self.session_id)
            print(f"PID file written: {os.getpid()}")
            
            # SCENARIO 2.6: Initialize database (handles corruption)
            try:
                self.db_mgr = DatabaseManager(
                    self.daemon_mgr.db_file,
                    max_records=self.max_records,
                    cleanup_interval=self.cleanup_interval
                )
                
                # Check integrity
                if not self.db_mgr.check_integrity():
                    print("WARNING: Database integrity check failed, recovering...")
                    # Recovery handled internally by db_manager
                
            except Exception as e:
                print(f"Database initialization failed: {e}")
                self._cleanup()
                return False
            
            # Log daemon start
            self.db_mgr.insert_immediate(
                timestamp=datetime.now().isoformat(),
                port="SYSTEM",
                data=f"DAEMON_STARTED (session: {self.session_id}) - No port connected yet",
                session_id=self.session_id
            )
            
            # Set running flag
            self.running = True
            
            print("=== Daemon started successfully (not monitoring any port yet) ===")
            return True
            
        except Exception as e:
            print(f"Unexpected error during startup: {e}")
            self._cleanup()
            return False
    
    def connect_port(self, port: str, baudrate: int = 115200) -> bool:
        """
        Connect to a serial port and start monitoring
        Can be called while daemon is running to switch ports
        
        Args:
            port: Serial port to monitor (e.g., "COM9")
            baudrate: Baud rate (default 115200)
        
        Returns:
            True if connected successfully, False otherwise
        """
        if not self.running:
            print("Cannot connect port: daemon not running")
            return False
        
        # Disconnect existing port if any
        if self.monitoring:
            print(f"Disconnecting from {self.current_port} before connecting to {port}")
            self.disconnect_port()
        
        print(f"=== Connecting to {port} @ {baudrate} baud ===")
        
        self.current_port = port
        self.current_baudrate = baudrate
        
        try:
            # Create serial handler
            self.serial_handler = SerialHandler(port, baudrate)
            
            # Setup callbacks
            self.serial_handler.on_data = self._on_serial_data
            self.serial_handler.on_connection_event = self._on_connection_event
            
            # Connect to port
            if not self.serial_handler.connect():
                print(f"Failed to connect to {port}")
                
                # Log error
                self.db_mgr.insert_immediate(
                    timestamp=datetime.now().isoformat(),
                    port=port,
                    data=f"PORT_CONNECTION_FAILED",
                    session_id=self.session_id
                )
                
                self.serial_handler = None
                self.current_port = None
                self.current_baudrate = None
                return False
            
            # Start reading thread
            self.serial_handler.start_reading()
            self.monitoring = True
            
            # Update PID file with current port
            self.daemon_mgr.write_pid(port, self.session_id)
            
            print(f"=== Successfully connected to {port} ===")
            return True
            
        except Exception as e:
            print(f"Unexpected error connecting to {port}: {e}")
            self.db_mgr.insert_immediate(
                timestamp=datetime.now().isoformat(),
                port=port,
                data=f"PORT_CONNECTION_ERROR: {e}",
                session_id=self.session_id
            )
            self.serial_handler = None
            self.current_port = None
            self.current_baudrate = None
            return False
    
    def disconnect_port(self) -> bool:
        """
        Disconnect from current serial port (releases port for other tools)
        Daemon continues running
        
        Returns:
            True if disconnected successfully, False otherwise
        """
        if not self.monitoring:
            print("No port currently connected")
            return True
        
        print(f"=== Disconnecting from {self.current_port} ===")
        
        try:
            # Stop serial reading
            if self.serial_handler:
                self.serial_handler.stop_reading()
                self.serial_handler.disconnect()
                self.serial_handler = None
            
            # Log disconnect
            self.db_mgr.insert_immediate(
                timestamp=datetime.now().isoformat(),
                port=self.current_port or "UNKNOWN",
                data=f"PORT_DISCONNECTED_BY_USER",
                session_id=self.session_id
            )
            
            # Update PID file (no port)
            self.daemon_mgr.write_pid("NONE", self.session_id)
            
            print(f"=== Disconnected from {self.current_port} ===")
            
            self.current_port = None
            self.current_baudrate = None
            self.monitoring = False
            
            return True
            
        except Exception as e:
            print(f"Error disconnecting: {e}")
            return False
    
    def run(self):
        """Main daemon loop (blocks until stopped)"""
        if not self.running:
            print("Daemon not started, cannot run")
            return
        
        print("Daemon running, press Ctrl+C to stop")
        print("Listening for commands...")
        
        try:
            # Main loop - process commands and flush database
            while self.running:
                # Check for incoming commands
                self._process_commands()
                
                # Periodic database flush (every second)
                if self.db_mgr:
                    self.db_mgr.flush()
                
                time.sleep(0.1)  # 100ms poll interval
        
        except KeyboardInterrupt:
            print("\nKeyboard interrupt received")
        
        finally:
            print("Main loop exited")
    
    def _process_commands(self):
        """Process any pending commands from command interface"""
        cmd = self.command_interface.check_for_command()
        
        if cmd is None:
            return
        
        command_name = cmd.get('command')
        print(f"Processing command: {command_name}")
        
        response = {'success': False, 'message': 'Unknown command'}
        
        try:
            if command_name == 'connect':
                port = cmd.get('port', 'COM9')
                baudrate = cmd.get('baudrate', 115200)
                success = self.connect_port(port, baudrate)
                response = {
                    'success': success,
                    'message': f'Connected to {port}' if success else f'Failed to connect to {port}',
                    'port': port if success else None,
                    'baudrate': baudrate if success else None
                }
            
            elif command_name == 'disconnect':
                success = self.disconnect_port()
                response = {
                    'success': success,
                    'message': 'Disconnected from port' if success else 'Failed to disconnect'
                }
            
            elif command_name == 'write':
                data = cmd.get('data', '')
                if not data:
                    response = {'success': False, 'message': 'No data provided to write'}
                elif not self.serial_handler or not self.serial_handler.is_connected():
                    response = {'success': False, 'message': 'Not connected to any port'}
                else:
                    success = self.serial_handler.write(data)
                    if success:
                        response = {
                            'success': True,
                            'message': f'Sent: {data}',
                            'data': data,
                            'length': len(data)
                        }
                    else:
                        response = {'success': False, 'message': 'Failed to write data'}
            
            elif command_name == 'status':
                status = self.get_status()
                response = {
                    'success': True,
                    'status': status
                }
            
            else:
                response = {
                    'success': False,
                    'error': 'UNKNOWN_COMMAND',
                    'message': f'Unknown command: {command_name}'
                }
        
        except Exception as e:
            response = {
                'success': False,
                'error': 'COMMAND_ERROR',
                'message': f'Error executing command: {e}'
            }
        
        # Send response
        self.command_interface.send_response(response)
    
    def stop(self):
        """Stop daemon gracefully (implements shutdown scenarios)"""
        if not self.running:
            return
        
        print("=== Stopping daemon ===")
        self.running = False
        
        # Log shutdown
        if self.db_mgr:
            try:
                self.db_mgr.insert_immediate(
                    timestamp=datetime.now().isoformat(),
                    port="SYSTEM",
                    data="DAEMON_STOPPED_CLEAN",
                    session_id=self.session_id
                )
            except Exception as e:
                print(f"Error logging shutdown: {e}")
        
        # Stop serial reading
        if self.serial_handler:
            try:
                self.serial_handler.stop_reading()
                self.serial_handler.disconnect()
            except Exception as e:
                print(f"Error stopping serial handler: {e}")
        
        # Cleanup
        self._cleanup()
        
        print("=== Daemon stopped ===")
    
    def _cleanup(self):
        """Clean up resources"""
        # Close database
        if self.db_mgr:
            try:
                self.db_mgr.close()
            except Exception as e:
                print(f"Error closing database: {e}")
        
        # Release lock and remove PID
        try:
            self.daemon_mgr.remove_pid()
            self.daemon_mgr.release_lock()
        except Exception as e:
            print(f"Error cleaning up daemon files: {e}")
    
    def _on_serial_data(self, data: str):
        """Callback for serial data (called from read thread)"""
        if self.db_mgr and self.current_port:
            try:
                self.db_mgr.insert(
                    timestamp=datetime.now().isoformat(),
                    port=self.current_port,
                    data=data,
                    session_id=self.session_id
                )
            except Exception as e:
                print(f"Error inserting data: {e}")
    
    def _on_connection_event(self, event: str):
        """Callback for connection events (called from read thread)"""
        print(f"Connection event: {event}")
        
        if self.db_mgr and self.current_port:
            try:
                self.db_mgr.insert_immediate(
                    timestamp=datetime.now().isoformat(),
                    port=self.current_port,
                    data=f"=== {event} ===",
                    session_id=self.session_id
                )
            except Exception as e:
                print(f"Error logging connection event: {e}")
    
    def get_status(self) -> dict:
        """
        Get current daemon status
        
        Returns:
            Dict with status information
        """
        return {
            'running': self.running,
            'monitoring': self.monitoring,
            'port': self.current_port,
            'baudrate': self.current_baudrate,
            'session_id': self.session_id
        }


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Serial Monitor Daemon")
    parser.add_argument("--port", default=None, help="Serial port to monitor (optional)")
    parser.add_argument("--baudrate", type=int, default=115200, help="Baud rate")
    parser.add_argument("--no-autoconnect", action="store_true", help="Don't auto-connect to port on startup")
    parser.add_argument("--max-records", type=int, default=10000, help="Maximum database records to keep (default: 10,000)")
    parser.add_argument("--cleanup-interval", type=int, default=60, help="Seconds between cleanup runs (default: 60)")
    
    args = parser.parse_args()
    
    # Create daemon (no port initially)
    daemon = SerialDaemon(
        max_records=args.max_records,
        cleanup_interval=args.cleanup_interval
    )
    
    # Start daemon
    if not daemon.start():
        print("Failed to start daemon")
        sys.exit(1)
    
    # Auto-connect to port if specified
    if args.port and not args.no_autoconnect:
        print(f"Auto-connecting to {args.port}...")
        if not daemon.connect_port(args.port, args.baudrate):
            print(f"Warning: Failed to connect to {args.port}, daemon will continue running")
    
    # Run main loop
    try:
        daemon.run()
    except Exception as e:
        print(f"Daemon error: {e}")
        daemon.stop()
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
