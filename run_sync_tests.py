#!/usr/bin/env python3
"""Run tests for player list synchronization"""

import sys
import unittest
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_sync_tests():
    """Run all synchronization tests"""
    print("Running Player List Synchronization Tests...")
    print("=" * 60)
    
    # Create test loader
    loader = unittest.TestLoader()
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add test modules
    try:
        # Core logic tests (no UI dependencies)
        from tests import test_player_sync_logic
        suite.addTests(loader.loadTestsFromModule(test_player_sync_logic))
        print("✓ Loaded core logic tests")
        
        # Try to load UI-dependent tests
        try:
            from tests import test_player_list_sync
            suite.addTests(loader.loadTestsFromModule(test_player_list_sync))
            print("✓ Loaded player list sync tests")
        except ImportError as e:
            print(f"⚠ Skipping UI tests (tkinter not available): {e}")
        
        try:
            from tests import test_draft_player_sync_integration
            suite.addTests(loader.loadTestsFromModule(test_draft_player_sync_integration))
            print("✓ Loaded integration tests")
        except ImportError as e:
            print(f"⚠ Skipping integration tests: {e}")
            
        try:
            from tests import test_rollback_sync_issue
            suite.addTests(loader.loadTestsFromModule(test_rollback_sync_issue))
            print("✓ Loaded rollback sync tests")
        except ImportError as e:
            print(f"⚠ Skipping rollback tests: {e}")
        
    except ImportError as e:
        print(f"Error importing core tests: {e}")
        return False
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailed tests:")
        for test, trace in result.failures:
            print(f"  - {test}")
            
    if result.errors:
        print("\nErrors:")
        for test, trace in result.errors:
            print(f"  - {test}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_sync_tests()
    sys.exit(0 if success else 1)