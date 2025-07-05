#!/usr/bin/env python3
"""Test the player stats popup display"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.player_generator import generate_mock_players
from src.models import Player

def test_popup_display():
    """Test if the popup would display stats correctly"""
    print("=== Testing Player Stats Popup Display ===\n")
    
    # Generate players
    players = generate_mock_players()
    print(f"Generated {len(players)} players")
    
    # Find players with stats
    players_with_stats = []
    for player in players[:20]:  # Check first 20
        if hasattr(player, 'weekly_stats_2024') and player.weekly_stats_2024:
            players_with_stats.append(player)
    
    print(f"\nFound {len(players_with_stats)} players with weekly stats in first 20")
    
    if not players_with_stats:
        print("ERROR: No players have weekly stats!")
        return False
    
    # Simulate what the popup would show
    test_player = players_with_stats[0]
    print(f"\n=== Simulating popup for {test_player.name} ===")
    print(f"Position: {test_player.position}")
    print(f"Team: {test_player.team}")
    print(f"2024 Total: {test_player.points_2024:.1f} pts" if test_player.points_2024 else "2024 Total: N/A")
    print(f"Games: {test_player.games_2024}" if test_player.games_2024 else "Games: N/A")
    
    if test_player.games_2024 and test_player.points_2024:
        print(f"Average: {test_player.points_2024/test_player.games_2024:.1f} pts/game")
    
    print(f"\nWeekly Stats ({len(test_player.weekly_stats_2024)} weeks):")
    print("-" * 60)
    print(f"{'Week':<6} {'Opponent':<10} {'Points':<8}", end="")
    
    # Position-specific headers
    if test_player.position == 'QB':
        print(f" {'Pass Yds':<10} {'Pass TD':<8} {'INT':<5} {'Rush Yds':<10} {'Rush TD':<8}")
    elif test_player.position in ['RB', 'WR', 'TE']:
        print(f" {'Rush Yds':<10} {'Rush TD':<8} {'Rec':<5} {'Rec Yds':<10} {'Rec TD':<8}")
    else:
        print()
    
    print("-" * 60)
    
    # Show first 5 weeks
    for week_data in test_player.weekly_stats_2024[:5]:
        week = week_data['week']
        opponent = week_data['opponent']
        stats = week_data.get('stats', {})
        points = stats.get('pts_ppr', 0)
        
        print(f"{week:<6} {opponent:<10} {points:<8.1f}", end="")
        
        # Position-specific stats
        if test_player.position == 'QB':
            pass_yds = stats.get('pass_yd', 0)
            pass_td = stats.get('pass_td', 0)
            pass_int = stats.get('pass_int', 0)
            rush_yds = stats.get('rush_yd', 0)
            rush_td = stats.get('rush_td', 0)
            print(f" {pass_yds:<10.0f} {pass_td:<8.0f} {pass_int:<5.0f} {rush_yds:<10.0f} {rush_td:<8.0f}")
        elif test_player.position in ['RB', 'WR', 'TE']:
            rush_yds = stats.get('rush_yd', 0)
            rush_td = stats.get('rush_td', 0)
            rec = stats.get('rec', 0)
            rec_yds = stats.get('rec_yd', 0)
            rec_td = stats.get('rec_td', 0)
            print(f" {rush_yds:<10.0f} {rush_td:<8.0f} {rec:<5.0f} {rec_yds:<10.0f} {rec_td:<8.0f}")
        else:
            print()
    
    print("-" * 60)
    print("\nIf you see data above, the popup should display correctly.")
    
    # Test multiple players to ensure consistency
    print(f"\n=== Testing consistency across multiple players ===")
    for i, player in enumerate(players_with_stats[:5]):
        weeks = len(player.weekly_stats_2024)
        print(f"{i+1}. {player.name} ({player.position}): {weeks} weeks of data")
        if weeks > 0:
            first_week = player.weekly_stats_2024[0]
            stats = first_week.get('stats', {})
            pts = stats.get('pts_ppr', 0)
            print(f"   Week {first_week['week']} vs {first_week['opponent']}: {pts:.1f} pts")
    
    return True

def test_player_attributes():
    """Test that Player objects have all required attributes"""
    print("\n\n=== Testing Player Attributes ===")
    
    players = generate_mock_players()
    
    # Check a player with stats
    player_with_stats = None
    for p in players:
        if hasattr(p, 'weekly_stats_2024') and p.weekly_stats_2024:
            player_with_stats = p
            break
    
    if not player_with_stats:
        print("ERROR: No player has weekly stats!")
        return False
    
    print(f"Testing player: {player_with_stats.name}")
    
    # Check all required attributes
    attributes = [
        ('name', str),
        ('position', str),
        ('rank', int),
        ('adp', float),
        ('team', (str, type(None))),
        ('player_id', (str, type(None))),
        ('games_2024', (int, type(None))),
        ('points_2024', (float, type(None))),
        ('weekly_stats_2024', (list, type(None)))
    ]
    
    all_good = True
    for attr_name, expected_type in attributes:
        if hasattr(player_with_stats, attr_name):
            value = getattr(player_with_stats, attr_name)
            if value is not None and not isinstance(value, expected_type):
                print(f"ERROR: {attr_name} has wrong type. Expected {expected_type}, got {type(value)}")
                all_good = False
            else:
                print(f"✓ {attr_name}: {type(value).__name__} = {value if attr_name != 'weekly_stats_2024' else f'[{len(value)} entries]' if value else None}")
        else:
            print(f"ERROR: Missing attribute {attr_name}")
            all_good = False
    
    return all_good

def main():
    """Run all display tests"""
    success = True
    
    success &= test_popup_display()
    success &= test_player_attributes()
    
    if success:
        print("\n\n=== All tests passed! ===")
        print("The popup should display weekly stats correctly.")
    else:
        print("\n\n=== Some tests failed! ===")
        print("There are issues that need to be fixed.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)