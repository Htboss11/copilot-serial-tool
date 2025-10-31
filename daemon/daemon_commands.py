"""
Daemon Command Interface
Allows external processes to send commands to the running daemon
"""
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any


class DaemonCommands:
    """Command interface for daemon control"""
    
    def __init__(self, command_dir: Optional[Path] = None):
        """
        Initialize command interface
        
        Args:
            command_dir: Directory for command files (default: ~/.serial-monitor/)
        """
        if command_dir is None:
            command_dir = Path.home() / ".serial-monitor"
        
        self.command_dir = Path(command_dir)
        self.command_dir.mkdir(parents=True, exist_ok=True)
        
        self.command_file = self.command_dir / "daemon_command.json"
        self.response_file = self.command_dir / "daemon_response.json"
    
    def send_command(self, command: str, **kwargs) -> Dict[str, Any]:
        """
        Send command to daemon and wait for response
        
        Args:
            command: Command name (connect, disconnect, status)
            **kwargs: Command arguments
        
        Returns:
            Response dictionary
        """
        # Create command
        cmd_data = {
            'command': command,
            'timestamp': time.time(),
            **kwargs
        }
        
        # Clear old response
        if self.response_file.exists():
            self.response_file.unlink()
        
        # Write command file
        with open(self.command_file, 'w') as f:
            json.dump(cmd_data, f)
        
        # Wait for response (timeout 5 seconds)
        for _ in range(50):
            time.sleep(0.1)
            if self.response_file.exists():
                try:
                    with open(self.response_file, 'r') as f:
                        response = json.load(f)
                    
                    # Clean up
                    self.response_file.unlink()
                    self.command_file.unlink()
                    
                    return response
                except Exception as e:
                    print(f"Error reading response: {e}")
                    break
        
        # Timeout
        if self.command_file.exists():
            self.command_file.unlink()
        
        return {
            'success': False,
            'error': 'TIMEOUT',
            'message': 'Daemon did not respond to command'
        }
    
    def check_for_command(self) -> Optional[Dict[str, Any]]:
        """
        Check if there's a pending command (called by daemon)
        
        Returns:
            Command dictionary or None
        """
        if not self.command_file.exists():
            return None
        
        try:
            with open(self.command_file, 'r') as f:
                cmd_data = json.load(f)
            return cmd_data
        except Exception as e:
            print(f"Error reading command file: {e}")
            return None
    
    def send_response(self, response: Dict[str, Any]):
        """
        Send response to command (called by daemon)
        
        Args:
            response: Response dictionary
        """
        try:
            with open(self.response_file, 'w') as f:
                json.dump(response, f)
        except Exception as e:
            print(f"Error writing response: {e}")
