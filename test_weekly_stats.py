#!/usr/bin/env python3
"""Test script to verify weekly stats are loading correctly"""

import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.player_data_fetcher import get_players_with_fallback, load_weekly_stats_2024
from src.utils.player_generator import generate_mock_players

def test_weekly_stats_loading():
    """Test if weekly stats are being loaded from the aggregated file"""
    print("Testing weekly stats loading...")
    
    # First, check if the aggregated file exists and has data
    stats_file = os.path.join('scripts', 'aggregated_player_stats_2024.json')
    if not os.path.exists(stats_file):
        print(f"ERROR: {stats_file} does not exist!")
        return False
        
    with open(stats_file, 'r') as f:
        aggregated_data = json.load(f)
    
    print(f"Aggregated stats file contains {len(aggregated_data)} players")
    
    # Check a sample player
    sample_player_id = list(aggregated_data.keys())[0]
    sample_data = aggregated_data[sample_player_id]
    print(f"\nSample player: {sample_data['player_name']}")
    print(f"Weekly stats count: {len(sample_data.get('weekly_stats', []))}")
    
    # Test the load_weekly_stats_2024 function
    weekly_stats_map = load_weekly_stats_2024()
    print(f"\nLoaded weekly stats for {len(weekly_stats_map)} player names")
    
    # Show some sample mappings
    sample_names = list(weekly_stats_map.keys())[:5]
    print(f"Sample name mappings: {sample_names}")
    
    return True

def test_player_data_integration():
    """Test if weekly stats are properly integrated into Player objects"""
    print("\n\nTesting player data integration...")
    
    # Get players with fallback (this should include weekly stats)
    players_data = get_players_with_fallback()
    print(f"Loaded {len(players_data)} players from data fetcher")
    
    # Check how many have weekly stats
    players_with_stats = 0
    players_without_stats = 0
    sample_players = []
    
    for player_data in players_data[:10]:  # Check first 10
        if 'weekly_stats_2024' in player_data and player_data['weekly_stats_2024']:
            players_with_stats += 1
            sample_players.append(player_data)
        else:
            players_without_stats += 1
            print(f"Player without stats: {player_data['name']}")
    
    print(f"\nPlayers with weekly stats: {players_with_stats}")
    print(f"Players without weekly stats: {players_without_stats}")
    
    if sample_players:
        player = sample_players[0]
        print(f"\nSample player with stats: {player['name']}")
        print(f"Number of weekly entries: {len(player['weekly_stats_2024'])}")
        if player['weekly_stats_2024']:
            print(f"First week data: {player['weekly_stats_2024'][0]}")
    
    return players_with_stats > 0

def test_generated_players():
    """Test if generated Player objects have weekly stats"""
    print("\n\nTesting generated Player objects...")
    
    players = generate_mock_players()
    print(f"Generated {len(players)} Player objects")
    
    # Check first 10 players
    players_with_stats = 0
    for i, player in enumerate(players[:10]):
        if hasattr(player, 'weekly_stats_2024') and player.weekly_stats_2024:
            players_with_stats += 1
            print(f"{player.name}: {len(player.weekly_stats_2024)} weekly entries")
        else:
            print(f"{player.name}: No weekly stats")
    
    print(f"\nTotal players with weekly stats: {players_with_stats}/10")
    
    # Show detailed stats for one player
    if players_with_stats > 0:
        for player in players[:10]:
            if hasattr(player, 'weekly_stats_2024') and player.weekly_stats_2024:
                print(f"\nDetailed stats for {player.name}:")
                for week in player.weekly_stats_2024[:3]:  # First 3 weeks
                    print(f"  Week {week['week']} vs {week['opponent']}: {week.get('stats', {}).get('pts_ppr', 'N/A')} pts")
                break
    
    return players_with_stats > 0

def main():
    """Run all tests"""
    print("=== Testing Weekly Stats Implementation ===\n")
    
    test_results = []
    
    # Run tests
    test_results.append(("Weekly stats loading", test_weekly_stats_loading()))
    test_results.append(("Player data integration", test_player_data_integration()))
    test_results.append(("Generated Player objects", test_generated_players()))
    
    # Summary
    print("\n\n=== Test Summary ===")
    for test_name, passed in test_results:
        status = "PASSED" if passed else "FAILED"
        print(f"{test_name}: {status}")
    
    all_passed = all(result[1] for result in test_results)
    if not all_passed:
        print("\nSome tests failed! The weekly stats feature is not working correctly.")
    else:
        print("\nAll tests passed!")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)