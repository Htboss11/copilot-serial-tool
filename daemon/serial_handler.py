"""
Serial Port Handler with Auto-Reconnect
Handles USB unplug/replug, timeouts, and error recovery
"""
import os
import sys
import time
from pathlib import Path
from typing import Optional, Callable
from datetime import datetime
from threading import Thread, Event

# === SETUP VENDORED PACKAGES ===
def setup_vendored_packages():
    """Add vendored packages to Python path"""
    daemon_dir = Path(__file__).parent
    vendor_dir = daemon_dir / "vendor"
    if vendor_dir.exists():
        for pkg in ["pyserial", "psutil", "mcp"]:
            pkg_path = vendor_dir / pkg
            if pkg_path.exists() and str(pkg_path) not in sys.path:
                sys.path.insert(0, str(pkg_path))

setup_vendored_packages()

import serial

# === DEBUG LOGGING ===
DEBUG = os.environ.get('SERIAL_DAEMON_DEBUG', '').lower() in ('1', 'true', 'yes')

def debug_log(component: str, message: str, level: str = "INFO"):
    """Centralized debug logging (only when DEBUG enabled)"""
    if DEBUG:
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] [{level}] [{component}] {message}", flush=True)


class SerialHandler:
    """Manages serial port connection with reconnection logic"""
    
    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 0.1,
                 rapid_retry_duration: int = 30, slow_retry_duration: int = 600,
                 echo_to_console: bool = False):
        """
        Initialize serial handler
        
        Args:
            port: Serial port name (e.g., "COM9")
            baudrate: Baud rate (default 115200)
            timeout: Read timeout in seconds (default 0.1)
            rapid_retry_duration: Duration for rapid retries in seconds (default 30)
            slow_retry_duration: Duration for slow retries in seconds (default 600 = 10 min)
            echo_to_console: If True, print serial data to console in real-time (default False)
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        
        self.ser: Optional[serial.Serial] = None
        self.running = False
        self.read_thread: Optional[Thread] = None
        self.stop_event = Event()
        
        # Two-stage reconnection settings
        self.rapid_retry_interval = 2.0  # seconds - Stage 1: fast retries
        self.rapid_retry_duration = rapid_retry_duration  # seconds - how long to do fast retries
        self.slow_retry_interval = 5.0  # seconds - Stage 2: slower retries
        self.slow_retry_duration = slow_retry_duration  # seconds - how long to do slow retries
        
        self.reconnect_start_time: Optional[float] = None
        
        # Idle detection
        self.last_data_time = time.time()
        self.idle_warning_threshold = 30  # seconds
        self.idle_timeout_threshold = 300  # seconds (5 minutes)
        
        # Live output settings
        self.echo_to_console = echo_to_console
        
        # Callbacks
        self.on_data: Optional[Callable[[str], None]] = None
        self.on_connection_event: Optional[Callable[[str], None]] = None
    
    def connect(self) -> bool:
        """
        Connect to serial port
        
        Returns:
            True if connected successfully, False otherwise
        """
        debug_log("SERIAL", f"Attempting connection to {self.port} @ {self.baudrate} baud")
        try:
            debug_log("SERIAL", f"Creating serial.Serial object...")
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                write_timeout=1.0
            )
            
            # Clear any stale data in buffers
            debug_log("SERIAL", "Clearing input/output buffers...")
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            
            debug_log("SERIAL", f"[SUCCESS] Connected to {self.port} @ {self.baudrate} baud", "SUCCESS")
            self.last_data_time = time.time()
            self.reconnect_count = 0
            
            if self.on_connection_event:
                self.on_connection_event("CONNECTION_ESTABLISHED")
            
            return True
            
        except serial.SerialException as e:
            debug_log("SERIAL", f"[ERROR] Failed to connect to {self.port}: {e}", "ERROR")
            if self.on_connection_event:
                self.on_connection_event(f"CONNECTION_FAILED: {e}")
            return False
        except Exception as e:
            debug_log("SERIAL", f"[ERROR] Unexpected error connecting to {self.port}: {e}", "ERROR")
            if self.on_connection_event:
                self.on_connection_event(f"CONNECTION_ERROR: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from serial port"""
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
                print(f"Disconnected from {self.port}")
                
                if self.on_connection_event:
                    self.on_connection_event("DISCONNECTED")
            except Exception as e:
                print(f"Error disconnecting: {e}")
    
    def is_connected(self) -> bool:
        """Check if serial port is connected"""
        return self.ser is not None and self.ser.is_open
    
    def set_echo(self, enabled: bool):
        """
        Enable or disable live console echo
        
        Args:
            enabled: True to echo serial data to console, False to disable
        """
        self.echo_to_console = enabled
        status = "enabled" if enabled else "disabled"
        debug_log("SERIAL", f"Console echo {status} for {self.port}")
        print(f"Console echo {status}")
    
    def start_reading(self):
        """Start reading thread"""
        if self.running:
            print("Reading thread already running")
            return
        
        self.running = True
        self.stop_event.clear()
        self.read_thread = Thread(target=self._read_loop, daemon=True)
        self.read_thread.start()
        print("Reading thread started")
    
    def stop_reading(self):
        """Stop reading thread"""
        if not self.running:
            return
        
        self.running = False
        self.stop_event.set()
        
        if self.read_thread:
            self.read_thread.join(timeout=2.0)
            if self.read_thread.is_alive():
                print("Warning: Read thread did not stop cleanly")
        
        print("Reading thread stopped")
    
    def _read_loop(self):
        """Main reading loop (runs in separate thread)"""
        consecutive_empty_reads = 0
        
        while self.running and not self.stop_event.is_set():
            try:
                # Ensure connected
                if not self.is_connected():
                    if not self._attempt_reconnect():
                        # Failed to reconnect, exit loop
                        break
                    continue
                
                # Read line with timeout
                try:
                    line = self.ser.readline()
                    
                    if line:
                        # Got data
                        decoded = line.decode('utf-8', errors='replace').rstrip('\r\n')
                        
                        if decoded:  # Non-empty line
                            self.last_data_time = time.time()
                            consecutive_empty_reads = 0
                            
                            # Echo to console if enabled
                            if self.echo_to_console:
                                try:
                                    # Try to print with UTF-8 encoding
                                    print(f"[{self.port}] {decoded}", flush=True)
                                except UnicodeEncodeError:
                                    # Fallback: encode to ASCII with backslashreplace
                                    safe_str = decoded.encode('ascii', errors='backslashreplace').decode('ascii')
                                    print(f"[{self.port}] {safe_str}", flush=True)
                            
                            if self.on_data:
                                self.on_data(decoded)
                    else:
                        # Empty read (timeout)
                        consecutive_empty_reads += 1
                        
                        # Check for idle state
                        idle_time = time.time() - self.last_data_time
                        
                        if idle_time > self.idle_timeout_threshold:
                            print(f"Port idle for {idle_time:.0f}s, attempting reconnect")
                            if self.on_connection_event:
                                self.on_connection_event("PORT_TIMEOUT")
                            
                            # Try to reconnect
                            self.disconnect()
                            if not self._attempt_reconnect():
                                break
                        
                        elif idle_time > self.idle_warning_threshold and consecutive_empty_reads % 300 == 0:
                            # Log idle warning periodically (every 30s at 0.1s timeout)
                            if self.on_connection_event:
                                self.on_connection_event(f"PORT_IDLE_WARNING: {idle_time:.0f}s")
                
                except serial.SerialException as e:
                    # Connection lost (USB unplugged, etc.)
                    print(f"Serial exception: {e}")
                    if self.on_connection_event:
                        self.on_connection_event(f"CONNECTION_LOST: {e}")
                    
                    self.disconnect()
                    
                    # Attempt reconnect
                    if not self._attempt_reconnect():
                        break
                
                except UnicodeDecodeError as e:
                    # Ignore decode errors, just skip this line
                    debug_log("SERIAL", "Decode error on serial data", "WARN")
                    continue
            
            except Exception as e:
                try:
                    error_msg = str(e)
                    print(f"Unexpected error in read loop: {error_msg}")
                    if self.on_connection_event:
                        self.on_connection_event(f"READ_ERROR: {error_msg}")
                except:
                    # Even error reporting failed - just log basic message
                    print("Unexpected error in read loop (encoding issue)")
                    if self.on_connection_event:
                        self.on_connection_event("READ_ERROR: encoding issue")
                
                # Brief pause before retrying
                time.sleep(1.0)
        
        print("Read loop exited")
    
    def _attempt_reconnect(self) -> bool:
        """
        Attempt to reconnect to serial port with two-stage retry strategy
        
        Stage 1: Rapid retries (every 2s) for configured duration (default 30s)
        Stage 2: Slow retries (every 5s) for configured duration (default 10 min)
        
        Returns:
            True if reconnected, False if all attempts failed
        """
        debug_log("SERIAL", f"Starting reconnection attempts to {self.port}")
        
        # Start tracking reconnection time
        if self.reconnect_start_time is None:
            self.reconnect_start_time = time.time()
        
        reconnect_attempt = 0
        
        while self.running:
            elapsed = time.time() - self.reconnect_start_time
            
            # Determine which stage we're in and set retry interval
            if elapsed < self.rapid_retry_duration:
                # Stage 1: Rapid retries
                retry_interval = self.rapid_retry_interval
                stage = "RAPID"
                time_remaining = self.rapid_retry_duration - elapsed
            elif elapsed < (self.rapid_retry_duration + self.slow_retry_duration):
                # Stage 2: Slow retries
                retry_interval = self.slow_retry_interval
                stage = "SLOW"
                time_remaining = (self.rapid_retry_duration + self.slow_retry_duration) - elapsed
            else:
                # Time expired - give up
                total_time = elapsed
                debug_log("SERIAL", 
                         f"Reconnection timeout after {total_time:.1f}s ({reconnect_attempt} attempts)", 
                         "ERROR")
                print(f"Failed to reconnect after {total_time:.1f}s ({reconnect_attempt} attempts)")
                
                if self.on_connection_event:
                    self.on_connection_event(
                        f"CONNECTION_FAILED_PERMANENT (time: {total_time:.1f}s, attempts: {reconnect_attempt})"
                    )
                
                self.reconnect_start_time = None
                return False
            
            reconnect_attempt += 1
            debug_log("SERIAL", 
                     f"Reconnect attempt {reconnect_attempt} [{stage}] (elapsed: {elapsed:.1f}s, remaining: {time_remaining:.1f}s)")
            print(f"Reconnect attempt {reconnect_attempt} [{stage}] - {time_remaining:.0f}s remaining")
            
            # Check if port is available again
            try:
                import serial.tools.list_ports
                ports = [p.device for p in serial.tools.list_ports.comports()]
                
                if self.port not in ports:
                    debug_log("SERIAL", f"Port {self.port} not available yet")
                else:
                    # Port available, try to connect
                    debug_log("SERIAL", f"Port {self.port} detected, attempting connection...")
                    if self.connect():
                        debug_log("SERIAL", 
                                 f"[SUCCESS] Reconnected after {elapsed:.1f}s ({reconnect_attempt} attempts)", 
                                 "SUCCESS")
                        if self.on_connection_event:
                            self.on_connection_event(
                                f"CONNECTION_RESTORED (time: {elapsed:.1f}s, attempts: {reconnect_attempt})"
                            )
                        
                        # Reset reconnection timer
                        self.reconnect_start_time = None
                        return True
            
            except Exception as e:
                debug_log("SERIAL", f"Error checking port availability: {e}", "ERROR")
                print(f"Error checking port availability: {e}")
            
            # Wait before next attempt
            time.sleep(retry_interval)
        
        # Loop exited due to running=False (daemon shutdown)
        debug_log("SERIAL", "Reconnection aborted - daemon stopping")
        self.reconnect_start_time = None
        return False
    
    def write(self, data: str) -> bool:
        """
        Write data to serial port
        
        Args:
            data: String to write (newline will be added)
        
        Returns:
            True if written successfully, False otherwise
        """
        if not self.is_connected():
            print("Cannot write: not connected")
            return False
        
        try:
            self.ser.write(data.encode('utf-8') + b'\n')
            self.ser.flush()
            return True
        except Exception as e:
            print(f"Error writing to serial port: {e}")
            return False
