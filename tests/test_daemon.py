"""
Integration Tests for Serial Daemon
Tests all startup, runtime, and shutdown scenarios
"""
import os
import sys
import time
import sqlite3
from pathlib import Path

# Add daemon to path
sys.path.insert(0, str(Path(__file__).parent.parent / "daemon"))

from mcp_daemon_tools import DaemonMCPTools


class TestResult:
    """Test result tracker"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def assert_true(self, condition, message):
        """Assert condition is true"""
        if condition:
            self.passed += 1
            print(f"  ✓ {message}")
        else:
            self.failed += 1
            error = f"  ✗ {message}"
            print(error)
            self.errors.append(error)
    
    def assert_false(self, condition, message):
        """Assert condition is false"""
        self.assert_true(not condition, message)
    
    def assert_equal(self, actual, expected, message):
        """Assert values are equal"""
        self.assert_true(actual == expected, f"{message} (expected: {expected}, got: {actual})")
    
    def summary(self):
        """Print test summary"""
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"Test Results: {self.passed}/{total} passed")
        if self.failed > 0:
            print(f"\nFailed tests:")
            for error in self.errors:
                print(error)
        print(f"{'='*60}\n")
        return self.failed == 0


def test_scenario_1_clean_start(tools: DaemonMCPTools, result: TestResult):
    """Test Scenario 2.1: Clean start from no running daemon"""
    print("\n[Test 1] Clean Start")
    
    # Ensure daemon is stopped
    tools.stop_daemon()
    time.sleep(0.5)
    
    # Check status (should not be running)
    status = tools.get_status()
    result.assert_false(status.get('running', False), "Daemon initially not running")
    
    # Start daemon
    start_result = tools.start_daemon(port='COM9', baudrate=115200)
    result.assert_true(start_result['success'], "Daemon starts successfully")
    result.assert_false(start_result.get('already_running', False), "Daemon was not already running")
    
    # Verify running
    status = tools.get_status()
    result.assert_true(status.get('running', False), "Daemon now running")
    result.assert_true('pid' in status, "Status includes PID")
    result.assert_true('session_id' in status, "Status includes session ID")


def test_scenario_2_already_running(tools: DaemonMCPTools, result: TestResult):
    """Test Scenario 2.2: Start when already running (idempotent)"""
    print("\n[Test 2] Already Running (Idempotent)")
    
    # Start again (should be idempotent)
    start_result = tools.start_daemon(port='COM9', baudrate=115200)
    result.assert_true(start_result['success'], "Start is idempotent")
    result.assert_true(start_result.get('already_running', False), "Detects already running")


def test_scenario_3_status_query(tools: DaemonMCPTools, result: TestResult):
    """Test status query returns correct info"""
    print("\n[Test 3] Status Query")
    
    status = tools.get_status()
    result.assert_true(status.get('running', False), "Daemon running")
    result.assert_true('uptime' in status, "Status includes uptime")
    result.assert_true('port' in status, "Status includes port")
    
    uptime = status.get('uptime', 0)
    result.assert_true(uptime > 0, f"Uptime is positive ({uptime:.2f}s)")


def test_scenario_4_database_writes(tools: DaemonMCPTools, result: TestResult):
    """Test that daemon is writing to database"""
    print("\n[Test 4] Database Writes")
    
    # Wait for some data to be captured
    print("  Waiting 5 seconds for data capture...")
    time.sleep(5)
    
    # Query database directly
    try:
        home = Path.home()
        db_path = home / ".serial-monitor" / "serial_data.db"
        
        result.assert_true(db_path.exists(), f"Database exists at {db_path}")
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("SELECT COUNT(*) FROM serial_data")
        count = cursor.fetchone()[0]
        conn.close()
        
        result.assert_true(count > 0, f"Database has rows ({count} lines captured)")
    
    except Exception as e:
        result.assert_true(False, f"Database query failed: {e}")


def test_scenario_5_query_tools(tools: DaemonMCPTools, result: TestResult):
    """Test MCP query tools"""
    print("\n[Test 5] MCP Query Tools")
    
    # Test get_recent
    recent = tools.get_recent(seconds=60)
    result.assert_true(recent['success'], "get_recent succeeds")
    result.assert_true('results' in recent, "get_recent returns results")
    print(f"  Got {recent['count']} recent lines")
    
    # Test get_tail
    tail = tools.get_tail(lines=10)
    result.assert_true(tail['success'], "get_tail succeeds")
    result.assert_true(len(tail['results']) <= 10, "get_tail respects limit")
    print(f"  Got {len(tail['results'])} tail lines")
    
    # Test custom query
    query_result = tools.query_data(
        "SELECT * FROM serial_data WHERE port = ? ORDER BY id DESC LIMIT 5",
        ['COM9']
    )
    result.assert_true(query_result['success'], "Custom query succeeds")
    print(f"  Custom query returned {query_result['count']} rows")


def test_scenario_6_graceful_stop(tools: DaemonMCPTools, result: TestResult):
    """Test Scenario 4.1: Graceful stop"""
    print("\n[Test 6] Graceful Stop")
    
    # Stop daemon
    stop_result = tools.stop_daemon()
    result.assert_true(stop_result['success'], "Stop succeeds")
    result.assert_true(stop_result.get('was_running', False), "Daemon was running")
    
    # Verify stopped
    status = tools.get_status()
    result.assert_false(status.get('running', False), "Daemon no longer running")


def test_scenario_7_stop_idempotent(tools: DaemonMCPTools, result: TestResult):
    """Test that stop is idempotent"""
    print("\n[Test 7] Stop Idempotent")
    
    # Stop again (should be idempotent)
    stop_result = tools.stop_daemon()
    result.assert_true(stop_result['success'], "Stop is idempotent")
    result.assert_false(stop_result.get('was_running', False), "Daemon was not running")


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("Serial Daemon Integration Tests")
    print("="*60)
    
    tools = DaemonMCPTools()
    result = TestResult()
    
    try:
        # Startup tests
        test_scenario_1_clean_start(tools, result)
        test_scenario_2_already_running(tools, result)
        test_scenario_3_status_query(tools, result)
        
        # Runtime tests
        test_scenario_4_database_writes(tools, result)
        test_scenario_5_query_tools(tools, result)
        
        # Shutdown tests
        test_scenario_6_graceful_stop(tools, result)
        test_scenario_7_stop_idempotent(tools, result)
    
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        tools.stop_daemon()
        sys.exit(1)
    
    except Exception as e:
        print(f"\n\nTest suite error: {e}")
        import traceback
        traceback.print_exc()
        tools.stop_daemon()
        sys.exit(1)
    
    # Print summary
    success = result.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
