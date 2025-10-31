# Files to Remove in Future Version

## Python TCP Server (Deprecated in v1.3.0)

The following files are **NO LONGER USED** as of version 1.3.0:

### python/serial_server.py
- **Status**: Deprecated - replaced by unified TypeScript architecture
- **Size**: ~17 KB
- **Why keeping temporarily**: Allows rollback if critical issues found
- **Remove in**: v1.4.0 or v2.0.0

### Test Scripts (Development only)
The following test scripts were created during development and can be removed:
- `test_server_flow.py` - Tests old TCP server
- `test_full_flow.py` - Tests old TCP server 
- `test_direct_read.py` - Direct serial test
- `check_and_disconnect.py` - Old server control
- `test_unified_arch.py` - Development test

**Keep**: `TEST_INSTRUCTIONS.py` - User-facing test guide

## Cleanup Plan

### v1.3.1 (Bug fix release)
- Keep all files for safety
- Monitor for issues

### v1.4.0 (Next feature release)
- Remove `python/serial_server.py`
- Remove development test scripts
- Update package.json to exclude from bundle
- Update .vscodeignore if needed

## Why Not Remove Now?

1. **Safety**: New architecture just deployed
2. **Rollback**: Can revert to v1.2.x approach if needed
3. **Testing**: User needs to verify functionality first
4. **Caution**: Better to have and not need than need and not have

## Current Package Impact

These unused files add ~17 KB to the VSIX package. Not significant enough to block release.

## Migration Verification

Before removing in v1.4.0, verify:
- ✅ Unified architecture stable for 2+ weeks
- ✅ No user reports of data loss
- ✅ Session logging works correctly
- ✅ Buffer functionality confirmed
- ✅ Auto-reconnect working (when implemented)
