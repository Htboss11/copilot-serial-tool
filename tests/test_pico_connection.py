"""
Test daemon connection to Raspberry Pi Pico on COM9
"""
import sys
import time
from pathlib import Path

# Add daemon directory
DAEMON_DIR = Path(__file__).parent / "daemon"
sys.path.insert(0, str(DAEMON_DIR))

from mcp_daemon_tools import DaemonMCPTools

print("=== Testing Daemon with Raspberry Pi Pico ===\n")

tools = DaemonMCPTools()

# Start daemon
print("1. Starting daemon...")
result = tools.start_daemon(auto_connect=False, max_records=1000, cleanup_interval=30)
print(f"   {result['message']}")
if not result['success']:
    sys.exit(1)

print(f"   PID: {result['info']['pid']}\n")

# Connect to COM9 (Raspberry Pi Pico)
print("2. Connecting to COM9 (Raspberry Pi Pico)...")
result = tools.connect_port(port="COM9", baudrate=115200)
print(f"   {result['message']}")

if not result['success']:
    print("   Connection failed!")
    print(f"   Error: {result.get('error', 'Unknown')}")
    tools.stop_daemon()
    sys.exit(1)

print("   ✓ Connected successfully!\n")

# Monitor for a bit
print("3. Monitoring serial output for 10 seconds...")
print("   (Plug in your device or send data via serial)")
time.sleep(10)

# Get recent data
print("\n4. Retrieving captured data...")
recent = tools.get_recent(seconds=10, limit=20)

if recent['success'] and recent['data']:
    print(f"   Captured {len(recent['data'])} lines:")
    for row in recent['data'][:10]:  # Show first 10
        print(f"   [{row[0]}] {row[2][:80]}")  # timestamp, data (truncated)
    if len(recent['data']) > 10:
        print(f"   ... and {len(recent['data']) - 10} more lines")
else:
    print("   No data captured yet")

# Status
print("\n5. Daemon status:")
status = tools.get_status()
print(f"   Running: {status['running']}")
print(f"   Port: {status['port']}")
print(f"   Lines captured: {status.get('lines_captured', 0)}")
print(f"   Uptime: {status['uptime']:.1f}s")

print("\n=== Test Complete ===")
print("Daemon is still running in background")
print("Check log: ~/.serial-monitor/daemon.log")
print("\nTo stop: python -c \"import sys; sys.path.insert(0, 'daemon'); from mcp_daemon_tools import DaemonMCPTools; DaemonMCPTools().stop_daemon()\"")
