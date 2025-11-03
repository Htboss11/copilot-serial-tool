"""
SQLite Database Manager for Serial Data
Handles concurrent access, WAL mode, write batching, corruption recovery, auto-cleanup
"""
import sqlite3
import time
from pathlib import Path
from typing import List, Dict, Optional, Any
from threading import Lock, Thread, Event
from datetime import datetime


class DatabaseManager:
    """Manages SQLite database for serial data with concurrency support"""
    
    def __init__(self, db_path: Path, max_records: int = 10000, cleanup_interval: int = 60):
        """
        Initialize database manager
        
        Args:
            db_path: Path to SQLite database file
            max_records: Maximum records to keep (default 10,000)
            cleanup_interval: Seconds between cleanup runs (default 60)
        """
        self.db_path = Path(db_path)
        self.connection = None
        self.write_lock = Lock()
        self.write_buffer = []
        self.buffer_size = 100  # Batch writes every 100 lines
        self.last_commit = time.time()
        self.commit_interval = 1.0  # Or every 1 second
        
        # Cleanup settings
        self.max_records = max_records
        self.cleanup_interval = cleanup_interval
        self.cleanup_thread: Optional[Thread] = None
        self.cleanup_stop_event = Event()
        
        # Initialize database
        self._init_database()
        
        # Start cleanup task
        self._start_cleanup_task()
    
    def _init_database(self):
        """Initialize database with schema and settings"""
        try:
            # Create database file if doesn't exist
            self.connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,  # Allow multi-threaded access
                timeout=10.0  # 10 second busy timeout
            )
            
            # Enable WAL mode for concurrent reads/writes
            self.connection.execute("PRAGMA journal_mode = WAL")
            self.connection.execute("PRAGMA synchronous = NORMAL")
            self.connection.execute("PRAGMA cache_size = 10000")
            self.connection.execute("PRAGMA busy_timeout = 5000")
            
            # Create schema
            self.connection.execute("""
                CREATE TABLE IF NOT EXISTS serial_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    port TEXT NOT NULL,
                    data TEXT NOT NULL,
                    session_id TEXT NOT NULL
                )
            """)
            
            # Create indexes for fast queries
            self.connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON serial_data(timestamp)
            """)
            
            self.connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_port 
                ON serial_data(port)
            """)
            
            self.connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_session 
                ON serial_data(session_id)
            """)
            
            self.connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_composite 
                ON serial_data(timestamp, port)
            """)
            
            self.connection.commit()
            
            print(f"Database initialized at {self.db_path}")
            
        except sqlite3.Error as e:
            print(f"Database initialization error: {e}")
            # Attempt corruption recovery
            self._recover_from_corruption()
    
    def _recover_from_corruption(self):
        """Attempt to recover from database corruption"""
        print("Attempting database corruption recovery...")
        
        try:
            # Close existing connection
            if self.connection:
                self.connection.close()
            
            # Rename corrupted database
            timestamp = int(time.time())
            backup_path = self.db_path.with_suffix(f'.corrupt.{timestamp}.db')
            
            if self.db_path.exists():
                self.db_path.rename(backup_path)
                print(f"Corrupted database moved to: {backup_path}")
            
            # Create new database
            self.connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=10.0
            )
            
            # Re-initialize schema
            self._init_database()
            
            # Log recovery event
            self.insert_immediate(
                timestamp=datetime.now().isoformat(),
                port="SYSTEM",
                data="DATABASE_RECOVERED_FROM_CORRUPTION",
                session_id="recovery"
            )
            
            print("Database recovery successful")
            
        except Exception as e:
            print(f"Database recovery failed: {e}")
            raise
    
    def check_integrity(self) -> bool:
        """
        Check database integrity
        
        Returns:
            True if database is intact, False if corrupted
        """
        try:
            cursor = self.connection.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            return result[0] == "ok"
        except Exception as e:
            print(f"Integrity check failed: {e}")
            return False
    
    def insert(self, timestamp: str, port: str, data: str, session_id: str):
        """
        Buffer data for batched insert (non-blocking)
        
        Args:
            timestamp: ISO format timestamp
            port: Serial port name
            data: Data line from serial port
            session_id: Current session identifier
        """
        with self.write_lock:
            self.write_buffer.append((timestamp, port, data, session_id))
            
            # Check if should commit
            should_commit = (
                len(self.write_buffer) >= self.buffer_size or
                time.time() - self.last_commit >= self.commit_interval
            )
            
            if should_commit:
                self._flush_buffer()
    
    def insert_immediate(self, timestamp: str, port: str, data: str, session_id: str):
        """
        Insert data immediately without buffering (for important events)
        
        Args:
            timestamp: ISO format timestamp
            port: Serial port name
            data: Data line from serial port
            session_id: Current session identifier
        """
        with self.write_lock:
            try:
                self.connection.execute(
                    "INSERT INTO serial_data (timestamp, port, data, session_id) VALUES (?, ?, ?, ?)",
                    (timestamp, port, data, session_id)
                )
                self.connection.commit()
            except sqlite3.Error as e:
                print(f"Immediate insert error: {e}")
                # Try to recover
                if "corrupt" in str(e).lower():
                    self._recover_from_corruption()
    
    def _flush_buffer(self):
        """Flush write buffer to database (called with lock held)"""
        if not self.write_buffer:
            return
        
        try:
            # Begin transaction
            self.connection.execute("BEGIN")
            
            # Batch insert
            self.connection.executemany(
                "INSERT INTO serial_data (timestamp, port, data, session_id) VALUES (?, ?, ?, ?)",
                self.write_buffer
            )
            
            # Commit transaction
            self.connection.commit()
            
            # Clear buffer
            self.write_buffer.clear()
            self.last_commit = time.time()
            
        except sqlite3.Error as e:
            print(f"Batch insert error: {e}")
            
            # Rollback on error
            try:
                self.connection.rollback()
            except Exception:
                pass
            
            # Check for corruption
            if "corrupt" in str(e).lower() or "malformed" in str(e).lower():
                self._recover_from_corruption()
    
    def flush(self):
        """Force flush of write buffer (call before shutdown)"""
        with self.write_lock:
            self._flush_buffer()
    
    def query(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        Execute SELECT query and return results
        
        Args:
            sql: SQL SELECT statement
            params: Query parameters
        
        Returns:
            List of result rows as dictionaries
        """
        # Validate query is SELECT only
        sql_upper = sql.strip().upper()
        if not sql_upper.startswith("SELECT"):
            raise ValueError("Only SELECT queries allowed")
        
        # Forbidden keywords
        forbidden = ["DELETE", "UPDATE", "INSERT", "DROP", "ALTER", "CREATE"]
        for keyword in forbidden:
            if keyword in sql_upper:
                raise ValueError(f"Query contains forbidden keyword: {keyword}")
        
        try:
            # Use row factory for dict results
            self.connection.row_factory = sqlite3.Row
            cursor = self.connection.execute(sql, params)
            
            # Convert to list of dicts
            results = [dict(row) for row in cursor.fetchall()]
            
            # Reset row factory
            self.connection.row_factory = None
            
            return results
            
        except sqlite3.Error as e:
            print(f"Query error: {e}")
            raise
    
    def get_recent(self, seconds: int = 60, port: Optional[str] = None, 
                   session_id: Optional[str] = None, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Get recent data from last N seconds
        
        Args:
            seconds: Number of seconds to look back
            port: Optional port filter
            session_id: Optional session filter
            limit: Maximum rows to return
        
        Returns:
            List of recent data rows
        """
        # Calculate timestamp threshold
        threshold = datetime.fromtimestamp(time.time() - seconds).isoformat()
        
        # Build query
        sql = "SELECT * FROM serial_data WHERE timestamp >= ?"
        params = [threshold]
        
        if port:
            sql += " AND port = ?"
            params.append(port)
        
        if session_id:
            sql += " AND session_id = ?"
            params.append(session_id)
        
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        
        return self.query(sql, tuple(params))
    
    def get_tail(self, lines: int = 100, port: Optional[str] = None,
                 session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get last N lines (like tail command)
        
        Args:
            lines: Number of lines to return
            port: Optional port filter
            session_id: Optional session filter
        
        Returns:
            List of last N data rows
        """
        sql = "SELECT * FROM serial_data WHERE 1=1"
        params = []
        
        if port:
            sql += " AND port = ?"
            params.append(port)
        
        if session_id:
            sql += " AND session_id = ?"
            params.append(session_id)
        
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(lines)
        
        return self.query(sql, tuple(params))
    
    def get_line_count(self, session_id: Optional[str] = None) -> int:
        """
        Get total line count
        
        Args:
            session_id: Optional session filter
        
        Returns:
            Total number of lines captured
        """
        if session_id:
            cursor = self.connection.execute(
                "SELECT COUNT(*) FROM serial_data WHERE session_id = ?",
                (session_id,)
            )
        else:
            cursor = self.connection.execute("SELECT COUNT(*) FROM serial_data")
        
        return cursor.fetchone()[0]
    
    def _cleanup_old_records(self):
        """
        Delete old records to keep database size manageable
        Keeps only the most recent max_records
        """
        try:
            # Get current record count
            cursor = self.connection.execute("SELECT COUNT(*) FROM serial_data")
            current_count = cursor.fetchone()[0]
            
            if current_count <= self.max_records:
                return  # No cleanup needed
            
            # Calculate how many to delete
            to_delete = current_count - self.max_records
            
            print(f"Database cleanup: {current_count:,} records, deleting oldest {to_delete:,}, keeping {self.max_records:,}")
            
            # Delete oldest records (keep most recent max_records)
            # This is efficient because we have an index on id (PRIMARY KEY)
            with self.write_lock:
                self.connection.execute(f"""
                    DELETE FROM serial_data 
                    WHERE id IN (
                        SELECT id FROM serial_data 
                        ORDER BY id ASC 
                        LIMIT {to_delete}
                    )
                """)
                self.connection.commit()
                
                # VACUUM to reclaim disk space (this can be slow, but necessary)
                print("Running VACUUM to reclaim disk space...")
                self.connection.execute("VACUUM")
                
            print(f"Cleanup complete. Database now has {self.max_records:,} records.")
            
        except Exception as e:
            print(f"Error during database cleanup: {e}")
    
    def _cleanup_task(self):
        """Background task that periodically cleans up old records"""
        print(f"Database cleanup task started (interval: {self.cleanup_interval}s, max records: {self.max_records:,})")
        
        while not self.cleanup_stop_event.is_set():
            # Wait for cleanup interval or stop event
            if self.cleanup_stop_event.wait(timeout=self.cleanup_interval):
                break  # Stop event was set
            
            # Perform cleanup
            try:
                self._cleanup_old_records()
            except Exception as e:
                print(f"Cleanup task error: {e}")
        
        print("Database cleanup task stopped")
    
    def _start_cleanup_task(self):
        """Start background cleanup task"""
        if self.cleanup_thread is None or not self.cleanup_thread.is_alive():
            self.cleanup_stop_event.clear()
            self.cleanup_thread = Thread(target=self._cleanup_task, daemon=True)
            self.cleanup_thread.start()
    
    def _stop_cleanup_task(self):
        """Stop background cleanup task"""
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            print("Stopping cleanup task...")
            self.cleanup_stop_event.set()
            self.cleanup_thread.join(timeout=5)
    
    def close(self):
        """Close database connection (flush first)"""
        # Stop cleanup task first
        self._stop_cleanup_task()
        
        if self.connection:
            try:
                # Flush any pending writes
                self.flush()
                
                # Close connection
                self.connection.close()
                print("Database connection closed")
            except Exception as e:
                print(f"Error closing database: {e}")
