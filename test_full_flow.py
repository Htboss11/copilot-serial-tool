#!/usr/bin/env python3
"""
Full flow test: Connect, wait, check buffer, check log file
"""
import socket
import json
import time
import os
from pathlib import Path

def cmd(method, params):
    s = socket.socket()
    s.connect(('localhost', 55556))
    s.sendall(json.dumps({'method': method, 'params': params}).encode())
    result = s.recv(4096).decode()
    s.close()
    return json.loads(result)

print("=" * 70)
print("FULL DATA FLOW TEST")
print("=" * 70)

# 1. Connect
print("\n[1] Connecting to COM9...")
result = cmd('connect', {'port': 'COM9', 'baudRate': 115200})
print(f"Connect result: {result.get('message')}")
log_file = result.get('logFile', 'N/A')
print(f"Log file: {log_file}")

# 2. Wait for data
print("\n[2] Waiting 10 seconds for data to accumulate...")
for i in range(10, 0, -1):
    print(f"  {i}...", end='\r', flush=True)
    time.sleep(1)
print("  Done!   ")

# 3. Check buffer
print("\n[3] Checking buffer...")
result = cmd('get_buffer', {'port': 'COM9'})
if result.get('success'):
    data = result.get('data', [])
    print(f"Buffer contains {len(data)} entries")
    if len(data) > 0:
        print("First 3 entries:")
        for entry in data[:3]:
            print(f"  [{entry.get('timestamp')}] {entry.get('data')[:60]}")
        print("Last 3 entries:")
        for entry in data[-3:]:
            print(f"  [{entry.get('timestamp')}] {entry.get('data')[:60]}")
    else:
        print("⚠️ BUFFER IS EMPTY - No data captured!")
else:
    print(f"Error: {result.get('error')}")

# 4. Check log file
print("\n[4] Checking log file...")
if log_file != 'N/A' and os.path.exists(log_file):
    with open(log_file, 'r') as f:
        lines = f.readlines()
    print(f"Log file has {len(lines)} lines")
    if len(lines) > 10:
        print("Last 5 lines:")
        for line in lines[-5:]:
            print(f"  {line.rstrip()}")
    else:
        print("Log file contents:")
        for line in lines:
            print(f"  {line.rstrip()}")
else:
    print(f"⚠️ Log file not found or N/A")

# 5. Test read command
print("\n[5] Testing read command (5 seconds)...")
result = cmd('read', {'port': 'COM9', 'duration': 5})
if result.get('success'):
    print(f"Total lines: {result.get('total_lines')}")
    print(f"Lines added during read: {result.get('lines_during_read')}")
else:
    print(f"Error: {result.get('error')}")

# 6. Final buffer check
print("\n[6] Final buffer check...")
result = cmd('get_buffer', {'port': 'COM9'})
if result.get('success'):
    print(f"Buffer now contains {len(result.get('data', []))} entries")

print("\n" + "=" * 70)
print("TEST COMPLETE - Keep connection open for manual testing")
print("Run check_and_disconnect.py when done")
print("=" * 70)
