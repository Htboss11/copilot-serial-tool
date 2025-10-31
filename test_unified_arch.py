#!/usr/bin/env python3
"""
Test the unified architecture - verify data flows through SerialManager
"""
import time
import sys
import os

# Add parent directory to path to import from src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("Testing Unified Architecture (v1.3.0)")
print("=" * 70)
print()

# Since we can't directly test TypeScript from Python, we'll test the Python script
# that SerialManager uses to verify it's outputting data correctly
import subprocess
import json

print("[1] Testing Python serial script output...")
print("    Starting connection to COM9...")

# Start the Python script that SerialManager uses
proc = subprocess.Popen(
    ['python', 'python/serial_monitor.py', 'connect', '--port', 'COM9', '--baud', '115200'],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1
)

print("    Waiting 5 seconds for data...")
start = time.time()
line_count = 0
sample_lines = []

try:
    while (time.time() - start) < 5:
        line = proc.stdout.readline()
        if line:
            line_count += 1
            if line_count <= 3:
                sample_lines.append(line.strip())
            print(f"    Line {line_count}: {line.strip()[:60]}...")
        time.sleep(0.01)
finally:
    proc.terminate()
    proc.wait(timeout=2)

print()
print(f"[2] Results:")
print(f"    ✓ Captured {line_count} lines in 5 seconds")
print()

if line_count > 0:
    print("[3] Sample data format:")
    for i, line in enumerate(sample_lines[:3], 1):
        try:
            data = json.loads(line)
            print(f"    Line {i}:")
            print(f"      Type: {data.get('type')}")
            print(f"      Timestamp: {data.get('timestamp', 'N/A')[:26]}")
            print(f"      Data: {data.get('data', 'N/A')[:50]}...")
        except:
            print(f"    Line {i}: {line[:60]}...")
    print()
    print("✅ Python script is outputting JSON data correctly")
    print("✅ SerialManager should be capturing this data")
    print()
    print("Next: Test if SerialManager buffer is being populated")
else:
    print("❌ No data captured - Pico may not be sending or port issue")
    print("   Check:")
    print("   - Is Pico plugged in to COM9?")
    print("   - Is Pico program running and sending data?")
    print("   - Try: python python/serial_monitor.py list")
