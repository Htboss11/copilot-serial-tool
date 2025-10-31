#!/usr/bin/env python3
"""
Test MCP Server for Serial Monitor Daemon
Simulates MCP client requests to test the server
"""

import json
import subprocess
import time
from typing import Dict, Any


class MCPServerTester:
    """Test harness for MCP server"""
    
    def __init__(self, server_script: str):
        self.server_script = server_script
        self.request_id = 0
    
    def get_next_id(self) -> int:
        """Get next request ID"""
        self.request_id += 1
        return self.request_id
    
    def make_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make JSON-RPC request"""
        request = {
            "jsonrpc": "2.0",
            "id": self.get_next_id(),
            "method": method
        }
        if params:
            request["params"] = params
        return request
    
    def send_request(self, proc, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send request and read response"""
        # Send request
        request_json = json.dumps(request) + "\n"
        proc.stdin.write(request_json.encode())
        proc.stdin.flush()
        
        # Read response
        response_line = proc.stdout.readline().decode()
        return json.loads(response_line)
    
    def test_server(self):
        """Run test suite"""
        print("=== Testing MCP Server for Serial Monitor Daemon ===\n")
        
        # Start MCP server process
        proc = subprocess.Popen(
            ["python", self.server_script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        try:
            # Test 1: Initialize
            print("Test 1: Initialize")
            req = self.make_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {}
            })
            resp = self.send_request(proc, req)
            print(f"✓ Initialize: {resp['result']['serverInfo']['name']}")
            print()
            
            # Test 2: List tools
            print("Test 2: List Tools")
            req = self.make_request("tools/list")
            resp = self.send_request(proc, req)
            tools = resp['result']['tools']
            print(f"✓ Found {len(tools)} tools:")
            for tool in tools:
                print(f"  - {tool['name']}: {tool['description'][:60]}...")
            print()
            
            # Test 3: Check daemon status
            print("Test 3: Check Daemon Status")
            req = self.make_request("tools/call", {
                "name": "serial_daemon_status",
                "arguments": {}
            })
            resp = self.send_request(proc, req)
            result = json.loads(resp['result']['content'][0]['text'])
            print(f"✓ Status: {json.dumps(result, indent=2)}")
            print()
            
            # Test 4: Start daemon (no auto-connect)
            print("Test 4: Start Daemon (no auto-connect)")
            req = self.make_request("tools/call", {
                "name": "serial_daemon_start",
                "arguments": {
                    "auto_connect": False
                }
            })
            resp = self.send_request(proc, req)
            result = json.loads(resp['result']['content'][0]['text'])
            print(f"✓ Start result: {result.get('message', 'Unknown')}")
            print(f"  Already running: {result.get('already_running', False)}")
            print()
            
            # Test 5: Check status again
            print("Test 5: Check Status After Start")
            req = self.make_request("tools/call", {
                "name": "serial_daemon_status",
                "arguments": {}
            })
            resp = self.send_request(proc, req)
            result = json.loads(resp['result']['content'][0]['text'])
            print(f"✓ Running: {result.get('running', False)}")
            print(f"  Monitoring: {result.get('monitoring', False)}")
            print(f"  Port: {result.get('port', 'NONE')}")
            print()
            
            print("=== All Tests Passed ===")
            
        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            # Cleanup
            proc.terminate()
            proc.wait(timeout=5)


if __name__ == "__main__":
    import sys
    import os
    
    # Get path to mcp_server.py
    script_dir = os.path.dirname(os.path.abspath(__file__))
    server_script = os.path.join(script_dir, "mcp_server.py")
    
    tester = MCPServerTester(server_script)
    tester.test_server()
