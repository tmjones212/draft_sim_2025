#!/usr/bin/env python3
"""Add player IDs from Sleeper data to players_2025.json"""

import json
import os
import sys

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.utils.player_extensions import format_name

def load_sleeper_players():
    """Load Sleeper player database"""
    with open('data/players.json', 'r') as f:
        return json.load(f)

def load_players_2025():
    """Load players_2025.json"""
    with open('src/data/players_2025.json', 'r') as f:
        return json.load(f)

def save_players_2025(data):
    """Save updated players_2025.json"""
    with open('src/data/players_2025.json', 'w') as f:
        json.dump(data, f, indent=2)

def main():
    # Load data
    sleeper_data = load_sleeper_players()
    players_data = load_players_2025()
    
    # Create name to player_id mapping from Sleeper data
    name_to_id = {}
    for player_id, player_info in sleeper_data.items():
        if 'name' in player_info:
            # Sleeper names are already uppercase
            name = player_info['name']
            name_to_id[name] = player_id
    
    # Update players with IDs
    matched = 0
    unmatched = []
    
    for player in players_data['players']:
        # Format the name to match Sleeper format
        formatted_name = format_name(player['name'])
        
        if formatted_name in name_to_id:
            player['player_id'] = name_to_id[formatted_name]
            matched += 1
        else:
            unmatched.append(f"{player['name']} ({formatted_name})")
    
    print(f"Matched {matched} players with IDs")
    print(f"Unmatched: {len(unmatched)} players")
    
    if unmatched:
        print("\nUnmatched players:")
        for name in unmatched[:10]:  # Show first 10
            print(f"  - {name}")
        if len(unmatched) > 10:
            print(f"  ... and {len(unmatched) - 10} more")
    
    # Save updated data
    save_players_2025(players_data)
    print(f"\nUpdated src/data/players_2025.json with player IDs")

if __name__ == "__main__":
    main()