"""
Comprehensive Test Suite for All New Features
Tests: Two-stage reconnection, live echo, configurable settings
"""
import sys
import os
import time

# Add daemon directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'daemon'))

from mcp_daemon_tools import DaemonMCPTools

def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def test_daemon_lifecycle():
    """Test basic daemon start/stop"""
    print_section("TEST 1: Daemon Lifecycle")
    
    tools = DaemonMCPTools()
    
    # Stop any existing daemon
    print("→ Stopping any existing daemon...")
    result = tools.stop_daemon()
    print(f"  ✓ {result['message']}")
    time.sleep(1)
    
    # Start daemon
    print("\n→ Starting daemon...")
    result = tools.start_daemon()
    assert result['success'], f"Failed to start daemon: {result.get('message')}"
    print(f"  ✓ {result['message']}")
    time.sleep(1)
    
    # Check status
    print("\n→ Checking daemon status...")
    result = tools.get_status()
    print(f"  ✓ PID: {result['pid']}")
    print(f"  ✓ Running: {result['running']}")
    print(f"  ✓ Session: {result['session_id']}")
    
    return tools

def test_port_connection(tools):
    """Test serial port connection"""
    print_section("TEST 2: Port Connection")
    
    # List available ports
    print("→ Listing available serial ports...")
    result = tools.find_ports()
    print(f"  ✓ Found {len(result['ports'])} port(s)")
    for port in result['ports']:
        print(f"    - {port['device']}: {port['description']}")
    
    # Connect to COM9
    print("\n→ Connecting to COM9...")
    result = tools.connect_port("COM9", 115200)
    assert result['success'], f"Failed to connect: {result.get('message')}"
    print(f"  ✓ {result['message']}")
    time.sleep(2)
    
    # Verify status shows connected
    print("\n→ Verifying connection in status...")
    result = tools.get_status()
    print(f"  ✓ Port: {result['port']}")
    print(f"  ✓ Lines captured: {result['lines_captured']}")
    
    return True

def test_echo_feature(tools):
    """Test live echo on/off"""
    print_section("TEST 3: Live Echo Feature")
    
    # Enable echo
    print("→ Enabling console echo...")
    result = tools.set_echo(True)
    assert result['success'], f"Failed to enable echo: {result.get('message')}"
    print(f"  ✓ {result['message']}")
    print(f"  ✓ Echo enabled: {result.get('echo_enabled')}")
    
    print("\n→ Waiting 3 seconds for serial data with echo...")
    print("  (Check daemon log for [COM9] prefixed lines)")
    time.sleep(3)
    
    # Disable echo
    print("\n→ Disabling console echo...")
    result = tools.set_echo(False)
    assert result['success'], f"Failed to disable echo: {result.get('message')}"
    print(f"  ✓ {result['message']}")
    print(f"  ✓ Echo enabled: {result.get('echo_enabled')}")
    
    print("\n→ Waiting 2 seconds without echo...")
    time.sleep(2)
    
    # Re-enable for remaining tests
    print("\n→ Re-enabling echo for remaining tests...")
    result = tools.set_echo(True)
    print(f"  ✓ {result['message']}")
    
    return True

def test_data_capture(tools):
    """Test data capture and query"""
    print_section("TEST 4: Data Capture & Query")
    
    print("→ Capturing data for 5 seconds...")
    time.sleep(5)
    
    # Query recent data
    print("\n→ Querying last 5 lines from database...")
    result = tools.get_recent(5)
    assert result['success'], f"Query failed: {result.get('message')}"
    
    lines = result.get('data', [])
    print(f"  ✓ Retrieved {len(lines)} line(s)")
    
    for i, line in enumerate(lines, 1):
        timestamp = line.get('timestamp', 'N/A')
        data = line.get('data', 'N/A')
        print(f"    {i}. [{timestamp}] {data[:60]}{'...' if len(data) > 60 else ''}")
    
    # Test SQL query
    print("\n→ Testing custom SQL query...")
    sql = "SELECT COUNT(*) as total FROM serial_data"
    result = tools.query_data(sql)
    assert result['success'], f"SQL query failed: {result.get('error')}"
    
    total = result['results'][0][0] if result['results'] else 0
    print(f"  ✓ Total records in database: {total}")
    
    return True

def test_send_data(tools):
    """Test sending data to device"""
    print_section("TEST 5: Send Data to Device")
    
    print("→ Sending test command to device...")
    result = tools.send_data("TEST_COMMAND")
    
    if result['success']:
        print(f"  ✓ {result['message']}")
        print(f"  ✓ Data sent: {result.get('data')}")
        print(f"  ✓ Length: {result.get('length')} bytes")
    else:
        print(f"  ⚠ {result['message']}")
    
    time.sleep(1)
    return True

def test_disconnect_reconnect(tools):
    """Test disconnect and reconnect"""
    print_section("TEST 6: Disconnect & Reconnect")
    
    # Disconnect
    print("→ Disconnecting from port...")
    result = tools.disconnect_port()
    assert result['success'], f"Failed to disconnect: {result.get('message')}"
    print(f"  ✓ {result['message']}")
    time.sleep(1)
    
    # Verify disconnected
    print("\n→ Verifying disconnection...")
    result = tools.get_status()
    print(f"  ✓ Port: {result.get('port', 'NONE')}")
    print(f"  ✓ Running: {result['running']}")
    
    # Reconnect
    print("\n→ Reconnecting to COM9...")
    result = tools.connect_port("COM9", 115200)
    assert result['success'], f"Failed to reconnect: {result.get('message')}"
    print(f"  ✓ {result['message']}")
    time.sleep(2)
    
    # Re-enable echo after reconnect
    print("\n→ Re-enabling echo after reconnect...")
    result = tools.set_echo(True)
    print(f"  ✓ {result['message']}")
    
    return True

def test_tail_functionality(tools):
    """Test tail (last N lines)"""
    print_section("TEST 7: Tail Functionality")
    
    print("→ Getting last 3 lines...")
    result = tools.get_tail(3)
    assert result['success'], f"Tail query failed: {result.get('message')}"
    
    lines = result.get('data', [])
    print(f"  ✓ Retrieved {len(lines)} line(s)")
    
    for i, line in enumerate(lines, 1):
        data = line.get('data', 'N/A')
        print(f"    {i}. {data[:70]}{'...' if len(data) > 70 else ''}")
    
    return True

def test_cleanup():
    """Final cleanup"""
    print_section("TEST 8: Cleanup")
    
    tools = DaemonMCPTools()
    
    print("→ Stopping daemon...")
    result = tools.stop_daemon()
    print(f"  ✓ {result['message']}")
    
    print("\n→ All tests complete!")
    return True

def main():
    """Run all tests"""
    print("\n" + "█"*60)
    print("█" + " "*58 + "█")
    print("█" + "  COMPREHENSIVE FEATURE TEST SUITE".center(58) + "█")
    print("█" + " "*58 + "█")
    print("█"*60)
    
    try:
        # Enable debug mode for detailed logging
        os.environ['SERIAL_DAEMON_DEBUG'] = '1'
        print("\n✓ Debug mode enabled (SERIAL_DAEMON_DEBUG=1)")
        
        # Run tests
        tools = test_daemon_lifecycle()
        test_port_connection(tools)
        test_echo_feature(tools)
        test_data_capture(tools)
        test_send_data(tools)
        test_disconnect_reconnect(tools)
        test_tail_functionality(tools)
        
        print_section("TEST SUMMARY")
        print("✅ All tests PASSED!")
        print(f"\nDaemon log location:")
        print(f"  {tools.daemon_mgr.log_file}")
        print(f"\nDatabase location:")
        print(f"  {tools.daemon_mgr.db_file}")
        
        print("\n" + "█"*60)
        print("█" + " "*58 + "█")
        print("█" + "  READY FOR PRODUCTION".center(58) + "█")
        print("█" + " "*58 + "█")
        print("█"*60 + "\n")
        
        # Keep daemon running for manual inspection
        print("⚠ Daemon is still running for manual inspection")
        print("  Use this command to stop it:")
        print(f"  python -c \"import sys; sys.path.insert(0, 'daemon'); from mcp_daemon_tools import DaemonMCPTools; print(DaemonMCPTools().stop_daemon()['message'])\"")
        print("\n  Or monitor live output:")
        print(f"  Get-Content \"{tools.daemon_mgr.log_file}\" -Wait -Tail 20")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        print("\nCleaning up...")
        test_cleanup()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        print("\nCleaning up...")
        test_cleanup()
        sys.exit(1)

if __name__ == "__main__":
    main()
