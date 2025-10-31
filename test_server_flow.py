#!/usr/bin/env python3
"""
Test script to verify the Python server data flow
Tests: connection, monitoring thread, buffer, and logging
"""

import socket
import json
import time
import sys

def send_command(command, params):
    """Send a command to the Python server"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('localhost', 55556))
        
        message = json.dumps({'method': command, 'params': params})
        sock.sendall(message.encode('utf-8'))
        
        # Receive response
        response = sock.recv(4096).decode('utf-8')
        sock.close()
        
        return json.loads(response)
    except Exception as e:
        return {'success': False, 'error': str(e)}

def main():
    print("=" * 60)
    print("TESTING SERIAL SERVER DATA FLOW")
    print("=" * 60)
    
    # Test 1: List ports
    print("\n[1] Testing list_ports...")
    result = send_command('list_ports', {})
    if isinstance(result, list):
        print(f"✓ Found {len(result)} ports")
        for port in result:
            print(f"  - {port.get('path')}: {port.get('description')}")
    else:
        print(f"✗ Error: {result}")
    
    # Test 2: Connect to COM9
    print("\n[2] Testing connect to COM9...")
    result = send_command('connect', {'port': 'COM9', 'baudRate': 115200})
    print(f"Result: {json.dumps(result, indent=2)}")
    if result.get('success'):
        print(f"✓ Connected successfully")
        print(f"  Log file: {result.get('logFile', 'N/A')}")
    else:
        print(f"✗ Failed: {result.get('error')}")
        return
    
    # Test 3: Wait for data to accumulate
    print("\n[3] Waiting 5 seconds for data to accumulate...")
    for i in range(5, 0, -1):
        print(f"  {i}...", end='\r')
        time.sleep(1)
    print("  Done!   ")
    
    # Test 4: Check buffer with get_buffer
    print("\n[4] Testing get_buffer...")
    result = send_command('get_buffer', {'port': 'COM9'})
    if result.get('success'):
        data = result.get('data', [])
        print(f"✓ Buffer contains {len(data)} entries")
        print(f"  Total lines: {result.get('total_lines')}")
        print(f"  Buffer seconds: {result.get('buffer_seconds')}")
        if data:
            print("\n  Last 5 entries:")
            for entry in data[-5:]:
                ts = entry.get('timestamp', 'N/A')
                line = entry.get('data', '')
                print(f"    [{ts}] {line[:60]}...")
        else:
            print("  ⚠️ Buffer is empty - monitoring thread may not be working")
    else:
        print(f"✗ Failed: {result.get('error')}")
    
    # Test 5: Test read command
    print("\n[5] Testing read command (5 second duration)...")
    result = send_command('read', {'port': 'COM9', 'duration': 5})
    if result.get('success'):
        print(f"✓ Read completed")
        print(f"  Duration: {result.get('duration')} seconds")
        print(f"  Total lines in buffer: {result.get('total_lines')}")
        print(f"  Lines added during read: {result.get('lines_during_read')}")
        
        data = result.get('data', [])
        if data:
            print(f"\n  Showing last 3 entries:")
            for entry in data[-3:]:
                ts = entry.get('timestamp', 'N/A')
                line = entry.get('data', '')
                print(f"    [{ts}] {line[:60]}...")
        else:
            print("  ⚠️ No data returned")
    else:
        print(f"✗ Failed: {result.get('error')}")
    
    # Test 6: Check status
    print("\n[6] Testing status...")
    result = send_command('status', {'port': 'COM9'})
    print(f"Result: {json.dumps(result, indent=2)}")
    
    # Test 7: Disconnect
    print("\n[7] Testing disconnect...")
    result = send_command('disconnect', {'port': 'COM9'})
    if result.get('success'):
        print(f"✓ Disconnected successfully")
    else:
        print(f"✗ Failed: {result.get('error')}")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == '__main__':
    main()
