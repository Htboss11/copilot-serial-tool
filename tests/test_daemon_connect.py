"""
Properly start daemon and connect to port with full debug output
"""
import sys
import time
from pathlib import Path

# Add daemon directory
DAEMON_DIR = Path(__file__).parent / "daemon"
sys.path.insert(0, str(DAEMON_DIR))

from mcp_daemon_tools import DaemonMCPTools, find_serial_ports, find_pico_ports

print("=== Starting Serial Monitor Daemon (Detached) ===\n")

# Create tools
tools = DaemonMCPTools()

# Start daemon (this will spawn as detached process)
print("1. Starting daemon...")
result = tools.start_daemon(auto_connect=False, max_records=1000, cleanup_interval=30)
print(f"   {result['message']}")

if not result['success']:
    print("   Failed to start daemon!")
    sys.exit(1)

info = result['info']
print(f"   PID: {info['pid']}")
print(f"   Session: {info['session_id']}")
print(f"   Port: {info['port']}")
print()

# List available ports
print("2. Available serial ports:")
ports = find_serial_ports()
for p in ports:
    vid = f"VID:0x{p['vid']:04X}" if p['vid'] else "VID:N/A"
    pid = f"PID:0x{p['pid']:04X}" if p['pid'] else "PID:N/A"
    print(f"   {p['device']}: {p['description']} ({vid} {pid})")
print()

# Check for Pico
print("3. Checking for Raspberry Pi Pico...")
pico_ports = find_pico_ports()
if pico_ports:
    print(f"   Found {len(pico_ports)} Pico device(s): {', '.join(pico_ports)}")
else:
    print("   No Pico devices found")
print()

# Connect to a port
if ports:
    port_to_connect = pico_ports[0] if pico_ports else ports[0]['device']
    print(f"4. Connecting to {port_to_connect}...")
    
    result = tools.connect_port(port=port_to_connect, baudrate=115200)
    print(f"   {result['message']}")
    
    if result['success']:
        print(f"   ✅ Connected successfully!")
        print()
        
        # Wait a moment for data
        print("5. Monitoring for 5 seconds...")
        time.sleep(5)
        
        # Check status
        status = tools.get_status()
        print(f"   Lines captured: {status.get('lines_captured', 0)}")
        print(f"   Uptime: {status['uptime']:.1f}s")
    else:
        print(f"   ❌ Connection failed")
else:
    print("   No ports available to connect to")

print("\n=== Daemon is running in background ===")
print("Check daemon.log for output: ~/.serial-monitor/daemon.log")
print("Use 'python test_daemon_isolation.py' to stop daemon")
