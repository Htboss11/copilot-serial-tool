"""
Test Live Serial Echo Feature
Demonstrates the ability to enable/disable live console output
"""
import sys
import os
import time

# Add daemon directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'daemon'))

from mcp_daemon_tools import DaemonMCPTools

def main():
    tools = DaemonMCPTools()
    
    print("=== Testing Live Serial Echo Feature ===\n")
    
    # Stop any existing daemon
    print("1. Stopping any existing daemon...")
    result = tools.stop_daemon()
    print(f"   {result['message']}")
    time.sleep(2)
    
    # Start daemon WITHOUT echo
    print("\n2. Starting daemon (echo DISABLED by default)...")
    result = tools.start_daemon()
    print(f"   {result['message']}")
    
    if not result['success']:
        print("Failed to start daemon!")
        return
    
    time.sleep(1)
    
    # Connect to COM9
    print("\n3. Connecting to COM9...")
    result = tools.connect_port("COM9", 115200)
    print(f"   {result['message']}")
    
    if not result['success']:
        print("Failed to connect!")
        return
    
    print("\n4. Serial data is now being captured to database")
    print("   But NOT printed to console (echo disabled)")
    print("   Waiting 5 seconds...")
    time.sleep(5)
    
    # Enable echo
    print("\n5. Enabling live console echo...")
    result = tools.set_echo(True)
    print(f"   {result['message']}")
    
    if result['success']:
        print("\n6. Serial data should now appear in daemon log:")
        print(f"   Log file: {tools.daemon_mgr.log_file}")
        print("   Format: [COM9] <serial data>")
        print("\n   Watching for 10 seconds...")
        time.sleep(10)
        
        # Disable echo
        print("\n7. Disabling live console echo...")
        result = tools.set_echo(False)
        print(f"   {result['message']}")
        
        print("\n8. Echo disabled - data still captured but not printed")
        print("   Waiting 5 seconds...")
        time.sleep(5)
    
    print("\n=== Test Complete ===")
    print("\nTo monitor the daemon log in real-time:")
    print(f"   Get-Content \"{tools.daemon_mgr.log_file}\" -Wait -Tail 20")
    print("\nTo query captured data:")
    print("   python -c \"import sys; sys.path.insert(0, 'daemon'); from mcp_daemon_tools import DaemonMCPTools; tools = DaemonMCPTools(); result = tools.get_recent(10); print(f'Last 10 lines: {result}')\"")
    print("\nTo stop daemon:")
    print("   python -c \"import sys; sys.path.insert(0, 'daemon'); from mcp_daemon_tools import DaemonMCPTools; print(DaemonMCPTools().stop_daemon()['message'])\"")

if __name__ == "__main__":
    main()
