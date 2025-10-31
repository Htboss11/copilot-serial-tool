"""
Quick script to forcefully disconnect from COM9
"""
import serial.tools.list_ports
import subprocess
import sys

# List all Python processes
print("Looking for serial monitor processes...")
result = subprocess.run(
    ['powershell', '-Command', 
     "Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -like '*serial_monitor*' -or $_.CommandLine -like '*COM9*'} | Select-Object ProcessId, CommandLine | ConvertTo-Json"],
    capture_output=True,
    text=True
)

print(result.stdout)
print("\nTo release COM9, you need to:")
print("1. Close any serial monitor terminals")
print("2. Reload VS Code window (Ctrl+R or Cmd+R)")
print("3. Or restart VS Code completely")
