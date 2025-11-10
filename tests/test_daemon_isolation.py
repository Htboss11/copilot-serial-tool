"""
Test script to verify daemon isolation from terminal signals
This script starts the daemon and then runs other commands to ensure the daemon stays alive
"""
import sys
import time
import subprocess
from pathlib import Path

# Add daemon directory to path
DAEMON_DIR = Path(__file__).parent / "daemon"
sys.path.insert(0, str(DAEMON_DIR))

from mcp_daemon_tools import DaemonMCPTools

def main():
    print("=== Testing Daemon Signal Isolation ===\n")
    
    tools = DaemonMCPTools()
    
    # Start daemon with debug enabled
    print("1. Starting daemon...")
    result = tools.start_daemon(auto_connect=False, max_records=1000, cleanup_interval=30)
    print(f"   Result: {result['message']}")
    
    if not result['success']:
        print("   ❌ Failed to start daemon")
        return
    
    print(f"   ✅ Daemon running (PID: {result['info']['pid']})\n")
    
    # Wait a moment
    time.sleep(1)
    
    # Run some Python commands (this used to kill the daemon)
    print("2. Running Python commands (this used to kill daemon)...")
    
    try:
        # Command 1: List ports
        print("   - Listing serial ports...")
        proc = subprocess.run(
            [sys.executable, "-c", "import serial.tools.list_ports; print('Ports:', len(list(serial.tools.list_ports.comports())))"],
            capture_output=True,
            text=True,
            timeout=5
        )
        print(f"     {proc.stdout.strip()}")
        
        # Command 2: Another Python command
        print("   - Running another Python command...")
        proc = subprocess.run(
            [sys.executable, "-c", "print('Hello from separate process')"],
            capture_output=True,
            text=True,
            timeout=5
        )
        print(f"     {proc.stdout.strip()}")
        
    except Exception as e:
        print(f"   ❌ Error running commands: {e}")
        return
    
    # Check if daemon still alive
    print("\n3. Checking daemon status...")
    status = tools.get_status()
    
    if status['running']:
        print(f"   ✅ Daemon still alive! (Uptime: {status['uptime']:.1f}s)")
        print(f"   ✅ Signal isolation working correctly!\n")
        
        # Stop daemon
        print("4. Stopping daemon...")
        stop_result = tools.stop_daemon()
        print(f"   {stop_result['message']}")
        
    else:
        print("   ❌ Daemon died! Signal isolation failed.\n")

if __name__ == "__main__":
    main()
