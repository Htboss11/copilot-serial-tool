#!/usr/bin/env python3
"""
Bootstrap script for Serial Monitor Daemon MCP Server
Adds vendored dependencies to Python path before importing main modules
"""
import sys
from pathlib import Path

def setup_vendored_packages():
    """Add vendored packages to Python path"""
    daemon_dir = Path(__file__).parent
    vendor_dir = daemon_dir / "vendor"
    
    # Add vendored packages to Python path
    vendor_packages = [
        vendor_dir / "pyserial",  # Contains serial/ package
        vendor_dir / "psutil",    # Contains psutil/ package  
        vendor_dir / "mcp",       # Contains mcp/ package
    ]
    
    for package_path in vendor_packages:
        if package_path.exists():
            # Add directory to sys.path so imports work
            path_str = str(package_path)
            if path_str not in sys.path:
                sys.path.insert(0, path_str)
        else:
            print(f"Warning: Vendored package not found: {package_path}", file=sys.stderr)

def main():
    """Bootstrap and run the MCP server"""
    # Setup vendored packages first
    setup_vendored_packages()
    
    # Now import and run the main MCP server
    try:
        import asyncio
        from mcp_server import main as run_mcp_server
        asyncio.run(run_mcp_server())
    except ImportError as e:
        print(f"Failed to import MCP server: {e}", file=sys.stderr)
        print("Make sure all dependencies are properly vendored.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()