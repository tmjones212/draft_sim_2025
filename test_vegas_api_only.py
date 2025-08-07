#!/usr/bin/env python3
"""Test script for Vegas props API only"""

import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import just the API module directly
from src.services.draftkings_api import DraftKingsAPI

def test_api():
    """Test DraftKings API"""
    print("Testing DraftKings API...")
    print("-" * 50)
    
    try:
        # Test getting all subcategories first
        print("Getting available prop categories...")
        subcategories = DraftKingsAPI.get_all_subcategories()
        print(f"Found {len(subcategories)} subcategories")
        
        for sub in subcategories[:10]:  # Show first 10
            print(f"  - {sub['name']} (ID: {sub['id']})")
        
        print("\n" + "-" * 50)
        
        # Test getting passing yards props
        print("\nGetting Passing Yards props...")
        passing_props = DraftKingsAPI.get_passing_yards_props()
        print(f"Found {len(passing_props)} passing yards props")
        
        if passing_props:
            print("\nTop 5 Passing Yards Props:")
            for prop in passing_props[:5]:
                print(f"  {prop.player_name} ({prop.team}): {prop.prop_value} yards")
                print(f"    Over: {prop.over_line}, Under: {prop.under_line}")
        
        # Test getting rushing yards props
        print("\n" + "-" * 50)
        print("\nGetting Rushing Yards props...")
        rushing_props = DraftKingsAPI.get_rushing_yards_props()
        print(f"Found {len(rushing_props)} rushing yards props")
        
        if rushing_props:
            print("\nTop 5 Rushing Yards Props:")
            for prop in rushing_props[:5]:
                print(f"  {prop.player_name}: {prop.prop_value} yards")
        
        # Test getting receiving yards props
        print("\n" + "-" * 50)
        print("\nGetting Receiving Yards props...")
        receiving_props = DraftKingsAPI.get_receiving_yards_props()
        print(f"Found {len(receiving_props)} receiving yards props")
        
        if receiving_props:
            print("\nTop 5 Receiving Yards Props:")
            for prop in receiving_props[:5]:
                print(f"  {prop.player_name}: {prop.prop_value} yards")
        
        # Test getting all common props at once
        print("\n" + "-" * 50)
        print("\nGetting all common props...")
        all_props = DraftKingsAPI.get_all_common_props()
        
        print("Summary of all props loaded:")
        for prop_type, props_list in all_props.items():
            print(f"  {prop_type}: {len(props_list)} props")
        
        print("\n" + "=" * 50)
        print("✓ API test successful!")
        return True
        
    except Exception as e:
        print(f"\n✗ API test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Vegas Props API Test")
    print("=" * 50)
    
    success = test_api()
    
    if not success:
        sys.exit(1)