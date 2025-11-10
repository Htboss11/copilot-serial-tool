"""
Test Two-Stage Reconnection Strategy
Tests rapid and slow retry behavior
"""
import sys
import os
import time

# Add daemon directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'daemon'))

from mcp_daemon_tools import DaemonMCPTools

def main():
    tools = DaemonMCPTools()
    
    print("=== Testing Two-Stage Reconnection Strategy ===\n")
    
    # Stop any existing daemon
    print("1. Stopping any existing daemon...")
    result = tools.stop_daemon()
    print(f"   {result['message']}")
    time.sleep(2)
    
    # Enable debug mode
    print("\n2. Enabling debug mode...")
    os.environ['SERIAL_DAEMON_DEBUG'] = '1'
    print("   Debug enabled")
    
    # Start daemon with custom retry settings
    print("\n3. Starting daemon with custom retry settings...")
    print("   - Rapid retry: 10 seconds (every 2s)")
    print("   - Slow retry: 20 seconds (every 5s)")
    print("   - Total timeout: 30 seconds")
    
    result = tools.start_daemon()
    print(f"   {result['message']}")
    
    if not result['success']:
        print("Failed to start daemon!")
        return
    
    time.sleep(1)
    
    # Try to connect to a non-existent port
    print("\n4. Connecting to non-existent port COM99...")
    print("   This will trigger reconnection attempts")
    print("   Watch the timing:\n")
    
    result = tools.connect_port("COM99", 115200)
    
    if result['success']:
        print("\n   Unexpected: Connection succeeded!")
    else:
        print(f"\n   Expected failure: {result['message']}")
    
    print("\n=== Test Instructions ===")
    print("1. Check the daemon log for reconnection attempts:")
    print(f"   Log file: {tools.daemon_mgr.log_file}")
    print("\n2. You should see:")
    print("   - Attempts 1-5: [RAPID] stage (2s intervals) for ~10s")
    print("   - Attempts 6-9: [SLOW] stage (5s intervals) for ~20s")
    print("   - Final message: CONNECTION_FAILED_PERMANENT after ~30s")
    print("\n3. Stop daemon when done:")
    print("   python -c \"import sys; sys.path.insert(0, 'daemon'); from mcp_daemon_tools import DaemonMCPTools; tools = DaemonMCPTools(); print(tools.stop_daemon()['message'])\"")
    
    print("\n=== Live Monitoring ===")
    print("To watch in real-time, run in another terminal:")
    print(f"   Get-Content \"{tools.daemon_mgr.log_file}\" -Wait -Tail 20")

if __name__ == "__main__":
    main()
