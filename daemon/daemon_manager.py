"""
Daemon PID and Lock File Management
Handles singleton enforcement across all VS Code instances
"""
import os
import sys
import time
import psutil
from pathlib import Path
from typing import Optional, Tuple


class DaemonManager:
    """Manages daemon singleton via PID file and file locking"""
    
    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialize daemon manager with base directory for PID/lock files
        
        Args:
            base_dir: Directory to store daemon files. Defaults to ~/.serial-monitor/
        """
        if base_dir is None:
            # System-wide location (not per-workspace)
            home = Path.home()
            base_dir = home / ".serial-monitor"
        
        self.base_dir = Path(base_dir)
        self.pid_file = self.base_dir / "daemon.pid"
        self.lock_file = self.base_dir / "daemon.lock"
        self.log_file = self.base_dir / "daemon.log"
        self.db_file = self.base_dir / "serial_data.db"
        
        # Ensure directory exists
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Lock file handle (kept open while daemon runs)
        self._lock_handle = None
    
    def acquire_lock(self) -> bool:
        """
        Acquire exclusive file lock (Windows-compatible)
        
        Returns:
            True if lock acquired, False if already held by another process
        """
        try:
            # Open lock file for write (create if doesn't exist)
            self._lock_handle = open(self.lock_file, 'w')
            
            # Try to acquire exclusive lock
            if sys.platform == 'win32':
                import msvcrt
                try:
                    # Lock first byte, non-blocking
                    msvcrt.locking(self._lock_handle.fileno(), msvcrt.LK_NBLCK, 1)
                    return True
                except OSError:
                    # Lock held by another process
                    self._lock_handle.close()
                    self._lock_handle = None
                    return False
            else:
                import fcntl
                try:
                    # Non-blocking exclusive lock
                    fcntl.flock(self._lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    return True
                except BlockingIOError:
                    self._lock_handle.close()
                    self._lock_handle = None
                    return False
        except Exception as e:
            print(f"Error acquiring lock: {e}", file=sys.stderr)
            if self._lock_handle:
                self._lock_handle.close()
                self._lock_handle = None
            return False
    
    def release_lock(self):
        """Release file lock and close handle"""
        if self._lock_handle:
            try:
                if sys.platform == 'win32':
                    import msvcrt
                    # Unlock first byte
                    msvcrt.locking(self._lock_handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self._lock_handle, fcntl.LOCK_UN)
            except Exception:
                pass  # Best effort
            finally:
                self._lock_handle.close()
                self._lock_handle = None
        
        # Remove lock file
        try:
            if self.lock_file.exists():
                self.lock_file.unlink()
        except Exception:
            pass  # Best effort
    
    def write_pid(self, port: str = "COM9", session_id: Optional[str] = None):
        """
        Write current process PID to file
        
        Format:
            <PID>
            <timestamp>
            <port>
            <session_id>
        
        Args:
            port: Serial port being monitored
            session_id: Unique session identifier
        """
        pid = os.getpid()
        timestamp = time.time()
        session_id = session_id or f"session_{int(timestamp)}"
        
        try:
            with open(self.pid_file, 'w') as f:
                f.write(f"{pid}\n")
                f.write(f"{timestamp}\n")
                f.write(f"{port}\n")
                f.write(f"{session_id}\n")
        except Exception as e:
            print(f"Error writing PID file: {e}", file=sys.stderr)
            raise
    
    def read_pid(self) -> Optional[Tuple[int, float, str, str]]:
        """
        Read PID file
        
        Returns:
            Tuple of (pid, timestamp, port, session_id) or None if file doesn't exist
        """
        if not self.pid_file.exists():
            return None
        
        try:
            with open(self.pid_file, 'r') as f:
                lines = f.readlines()
                if len(lines) >= 4:
                    pid = int(lines[0].strip())
                    timestamp = float(lines[1].strip())
                    port = lines[2].strip()
                    session_id = lines[3].strip()
                    return (pid, timestamp, port, session_id)
        except Exception as e:
            print(f"Error reading PID file: {e}", file=sys.stderr)
        
        return None
    
    def remove_pid(self):
        """Remove PID file"""
        try:
            if self.pid_file.exists():
                self.pid_file.unlink()
        except Exception as e:
            print(f"Error removing PID file: {e}", file=sys.stderr)
    
    def is_process_running(self, pid: int) -> bool:
        """
        Check if process with given PID exists
        
        Args:
            pid: Process ID to check
        
        Returns:
            True if process exists, False otherwise
        """
        try:
            return psutil.pid_exists(pid)
        except Exception:
            return False
    
    def cleanup_stale_files(self) -> bool:
        """
        Clean up stale PID and lock files from crashed daemon
        
        Returns:
            True if cleanup performed, False if daemon is running
        """
        pid_data = self.read_pid()
        
        if pid_data is None:
            # No PID file, check for orphaned lock
            if self.lock_file.exists():
                # Check if lock file is old (>5 minutes)
                try:
                    mtime = self.lock_file.stat().st_mtime
                    age = time.time() - mtime
                    if age > 300:  # 5 minutes
                        print(f"Removing orphaned lock file (age: {age:.0f}s)")
                        self.lock_file.unlink()
                        return True
                except Exception as e:
                    print(f"Error checking lock file: {e}", file=sys.stderr)
            return True
        
        pid, timestamp, port, session_id = pid_data
        
        # Check if process exists
        if self.is_process_running(pid):
            # Process exists, check if it's actually our daemon
            try:
                proc = psutil.Process(pid)
                cmdline = ' '.join(proc.cmdline())
                if 'serial_daemon' in cmdline or 'python' in cmdline.lower():
                    # Looks like our daemon, don't clean up
                    return False
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Process doesn't exist or isn't our daemon - clean up
        print(f"Cleaning up stale files from PID {pid}")
        self.remove_pid()
        
        # Try to remove lock file
        try:
            if self.lock_file.exists():
                self.lock_file.unlink()
        except Exception as e:
            print(f"Error removing lock file: {e}", file=sys.stderr)
        
        return True
    
    def check_daemon_health(self) -> bool:
        """
        Check if daemon is running and healthy
        
        Returns:
            True if daemon running and responsive, False otherwise
        """
        pid_data = self.read_pid()
        if pid_data is None:
            return False
        
        pid, timestamp, port, session_id = pid_data
        
        # Check if process exists
        if not self.is_process_running(pid):
            return False
        
        # TODO: Add TCP health check endpoint (optional)
        # For now, just check process exists
        
        return True
    
    def get_daemon_info(self) -> Optional[dict]:
        """
        Get information about running daemon
        
        Returns:
            Dict with daemon info or None if not running
        """
        pid_data = self.read_pid()
        if pid_data is None:
            return None
        
        pid, timestamp, port, session_id = pid_data
        
        if not self.is_process_running(pid):
            return None
        
        uptime = time.time() - timestamp
        
        return {
            'pid': pid,
            'port': port,
            'session_id': session_id,
            'start_time': timestamp,
            'uptime': uptime,
            'running': True
        }
