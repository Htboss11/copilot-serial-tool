#!/usr/bin/env python3
"""
Direct serial test - bypass the server and read directly
"""
import serial
import time

port = 'COM9'
baud = 115200

print(f"Opening {port} at {baud} baud...")
try:
    ser = serial.Serial(port, baud, timeout=1)
    print(f"✓ Port opened successfully")
    print(f"  in_waiting: {ser.in_waiting} bytes")
    print("\nReading for 5 seconds...")
    
    start_time = time.time()
    line_count = 0
    
    while (time.time() - start_time) < 5:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line:
                print(f"  [{line_count}] {line}")
                line_count += 1
        time.sleep(0.01)
    
    print(f"\nRead {line_count} lines in 5 seconds")
    ser.close()
    
except Exception as e:
    print(f"✗ Error: {e}")
