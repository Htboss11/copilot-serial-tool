"""
Serial Port Handler with Auto-Reconnect
Handles USB unplug/replug, timeouts, and error recovery
"""
import time
import serial
from typing import Optional, Callable
from datetime import datetime
from threading import Thread, Event


class SerialHandler:
    """Manages serial port connection with reconnection logic"""
    
    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 0.1):
        """
        Initialize serial handler
        
        Args:
            port: Serial port name (e.g., "COM9")
            baudrate: Baud rate (default 115200)
            timeout: Read timeout in seconds (default 0.1)
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        
        self.ser: Optional[serial.Serial] = None
        self.running = False
        self.read_thread: Optional[Thread] = None
        self.stop_event = Event()
        
        # Reconnection settings
        self.reconnect_interval = 2.0  # seconds
        self.max_reconnect_attempts = 10
        self.reconnect_count = 0
        
        # Idle detection
        self.last_data_time = time.time()
        self.idle_warning_threshold = 30  # seconds
        self.idle_timeout_threshold = 300  # seconds (5 minutes)
        
        # Callbacks
        self.on_data: Optional[Callable[[str], None]] = None
        self.on_connection_event: Optional[Callable[[str], None]] = None
    
    def connect(self) -> bool:
        """
        Connect to serial port
        
        Returns:
            True if connected successfully, False otherwise
        """
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                write_timeout=1.0
            )
            
            # Clear any stale data in buffers
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            
            print(f"Connected to {self.port} @ {self.baudrate} baud")
            self.last_data_time = time.time()
            self.reconnect_count = 0
            
            if self.on_connection_event:
                self.on_connection_event("CONNECTION_ESTABLISHED")
            
            return True
            
        except serial.SerialException as e:
            print(f"Failed to connect to {self.port}: {e}")
            if self.on_connection_event:
                self.on_connection_event(f"CONNECTION_FAILED: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error connecting to {self.port}: {e}")
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
                    print(f"Decode error: {e}")
                    continue
            
            except Exception as e:
                print(f"Unexpected error in read loop: {e}")
                if self.on_connection_event:
                    self.on_connection_event(f"READ_ERROR: {e}")
                
                # Brief pause before retrying
                time.sleep(1.0)
        
        print("Read loop exited")
    
    def _attempt_reconnect(self) -> bool:
        """
        Attempt to reconnect to serial port
        
        Returns:
            True if reconnected, False if all attempts failed
        """
        print(f"Attempting to reconnect to {self.port}")
        
        while self.running and self.reconnect_count < self.max_reconnect_attempts:
            self.reconnect_count += 1
            
            print(f"Reconnect attempt {self.reconnect_count}/{self.max_reconnect_attempts}")
            
            # Check if port is available again
            try:
                import serial.tools.list_ports
                ports = [p.device for p in serial.tools.list_ports.comports()]
                
                if self.port not in ports:
                    print(f"Port {self.port} not available yet")
                else:
                    # Port available, try to connect
                    if self.connect():
                        if self.on_connection_event:
                            self.on_connection_event(f"CONNECTION_RESTORED (attempt {self.reconnect_count})")
                        return True
            
            except Exception as e:
                print(f"Error checking port availability: {e}")
            
            # Wait before next attempt
            time.sleep(self.reconnect_interval)
        
        # All attempts failed
        print(f"Failed to reconnect after {self.reconnect_count} attempts")
        if self.on_connection_event:
            self.on_connection_event(f"CONNECTION_FAILED_PERMANENT (attempts: {self.reconnect_count})")
        
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
