#!/usr/bin/env python3
"""Test script for Vegas props integration"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.services.draftkings_api import DraftKingsAPI
from src.services.vegas_props_service import VegasPropsService

def test_api_direct():
    """Test DraftKings API directly"""
    print("Testing DraftKings API directly...")
    print("-" * 50)
    
    try:
        # Test getting passing yards props
        print("Getting Passing Yards props...")
        passing_props = DraftKingsAPI.get_passing_yards_props()
        print(f"Found {len(passing_props)} passing yards props")
        
        if passing_props:
            for prop in passing_props[:3]:  # Show first 3
                print(f"  {prop.player_name}: {prop.prop_value} yards")
                print(f"    Over: {prop.over_line}, Under: {prop.under_line}")
        
        # Test getting rushing yards props
        print("\nGetting Rushing Yards props...")
        rushing_props = DraftKingsAPI.get_rushing_yards_props()
        print(f"Found {len(rushing_props)} rushing yards props")
        
        if rushing_props:
            for prop in rushing_props[:3]:  # Show first 3
                print(f"  {prop.player_name}: {prop.prop_value} yards")
        
        print("\n✓ API test successful!")
        return True
        
    except Exception as e:
        print(f"\n✗ API test failed: {e}")
        return False

def test_service():
    """Test Vegas Props Service"""
    print("\nTesting Vegas Props Service...")
    print("-" * 50)
    
    try:
        service = VegasPropsService()
        
        # Wait a bit for background load
        import time
        print("Waiting for background load...")
        time.sleep(3)
        
        # Get all props
        all_props = service.get_all_props()
        print(f"Service loaded {len(all_props)} prop types")
        
        for prop_type, props_list in all_props.items():
            print(f"  {prop_type}: {len(props_list)} props")
        
        # Test getting props for specific players
        test_players = ["Josh Allen", "Saquon Barkley", "Justin Jefferson"]
        
        print("\nTesting player prop lookups:")
        for player_name in test_players:
            props = service.get_player_props(player_name)
            summary = service.get_summary_string(player_name)
            
            if props:
                print(f"\n{player_name}:")
                print(f"  Summary: {summary}")
                for prop_type, prop in props.items():
                    print(f"  {prop_type}: {service.format_prop_display(prop)}")
            else:
                print(f"\n{player_name}: No props found")
        
        print("\n✓ Service test successful!")
        return True
        
    except Exception as e:
        print(f"\n✗ Service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Vegas Props Integration Test")
    print("=" * 50)
    
    api_success = test_api_direct()
    service_success = test_service()
    
    print("\n" + "=" * 50)
    if api_success and service_success:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed")
        sys.exit(1)