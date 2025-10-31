"""
Quick test script to verify unified architecture works
Run this from VS Code terminal after extension loads
"""
print("""
TESTING INSTRUCTIONS FOR UNIFIED ARCHITECTURE v1.3.0
=====================================================

Since the extension is now installed (v1.3.0), test using GitHub Copilot:

METHOD 1 - Using GitHub Copilot Chat:
--------------------------------------
1. Open GitHub Copilot Chat (Ctrl+Alt+I or Cmd+Shift+I)
2. Type: "List available serial ports"
   - Should return list including COM9
3. Type: "Connect to COM9 at 115200 baud"
   - Should connect successfully
4. Type: "Read from COM9 for 5 seconds"
   - Should return data with timestamps
5. Type: "Get buffer from COM9"
   - Should return all buffered data (including historical)

METHOD 2 - Check Session Logs:
-------------------------------
1. Navigate to: workspace_root/serial-sessions/
2. Look for newest log file
3. Verify it contains:
   - Header with port/baud info
   - [timestamp] data lines
   - Connection markers

METHOD 3 - Check VS Code Output:
---------------------------------
1. Open View → Output
2. Select "Serial Monitor - COM9" from dropdown
3. Should see real-time data flowing

EXPECTED BEHAVIOR:
------------------
✅ Data appears in Copilot responses
✅ Data written to session log files
✅ Data stored in CircularBuffer (10 min retention)
✅ Connection markers appear in both places

DEBUGGING:
----------
If data not showing:
1. Check: Is Pico actually sending? (Power LED on?)
2. Check: Output panel shows "Serial Monitor - COM9"?
3. Check: Session files in serial-sessions/ folder?
4. Check: Any errors in VS Code Developer Console?
   (Help → Toggle Developer Tools → Console tab)

QUICK TESTS:
------------
From VS Code terminal, run:
  python python/serial_monitor.py list
  → Should show COM9

From Copilot Chat:
  "connect to com9"
  → Should succeed
  
  "read from com9 for 3 seconds"
  → Should return timestamped data

If these work: ✅ ARCHITECTURE IS FUNCTIONING!
""")
