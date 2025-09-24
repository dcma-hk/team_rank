#!/usr/bin/env python3
"""Simple test for snapshot functionality."""

import sys
import os

def test_snapshot_function():
    """Test the snapshot function."""
    print("Testing snapshot function...")
    
    try:
        from backend.models import get_current_snapshot
        current = get_current_snapshot()
        print(f"✓ Current snapshot: {current}")
        
        # Verify format
        if len(current) == 7 and current[4:] in ['H1', 'H2']:
            print("✓ Snapshot format is correct")
        else:
            print(f"✗ Invalid snapshot format: {current}")
            return False
            
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_sqlite_basic():
    """Test basic SQLite functionality."""
    print("\nTesting SQLite basic functionality...")
    
    try:
        from backend.sqlite_data_manager import SQLiteDataManager
        
        # Create test database
        db_path = "test_snapshot_basic.db"
        if os.path.exists(db_path):
            os.remove(db_path)
            
        dm = SQLiteDataManager(db_path)
        print("✓ SQLite data manager created")
        
        # Test current snapshot method
        current = dm.get_current_snapshot()
        print(f"✓ Current snapshot from data manager: {current}")
        
        # Clean up
        if os.path.exists(db_path):
            os.remove(db_path)
        print("✓ Test database cleaned up")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== Snapshot Functionality Test ===\n")
    
    success = True
    
    if not test_snapshot_function():
        success = False
    
    if not test_sqlite_basic():
        success = False
    
    if success:
        print("\n✓ All snapshot tests passed!")
    else:
        print("\n✗ Some tests failed!")
        sys.exit(1)
