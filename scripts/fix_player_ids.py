#!/usr/bin/env python3
"""Fix player IDs in players_2025.json to match correct players by position"""

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
    
    # Create name+position to player_id mapping from Sleeper data
    name_pos_to_id = {}
    name_to_candidates = {}  # Track all candidates for each name
    
    for player_id, player_info in sleeper_data.items():
        if 'name' in player_info and 'position' in player_info:
            name = player_info['name']
            position = player_info['position']
            key = (name, position)
            name_pos_to_id[key] = player_id
            
            # Track all candidates
            if name not in name_to_candidates:
                name_to_candidates[name] = []
            name_to_candidates[name].append({
                'id': player_id,
                'position': position,
                'team': player_info.get('team', 'N/A')
            })
    
    # Update players with IDs
    matched = 0
    fixed = 0
    unmatched = []
    
    for player in players_data['players']:
        # Format the name to match Sleeper format
        formatted_name = format_name(player['name'])
        position = player['position']
        
        # Try exact match with position
        key = (formatted_name, position)
        if key in name_pos_to_id:
            old_id = player.get('player_id')
            new_id = name_pos_to_id[key]
            if old_id != new_id:
                print(f"FIXING: {player['name']} ({position}) - ID {old_id} -> {new_id}")
                fixed += 1
            player['player_id'] = new_id
            matched += 1
        else:
            # Check if there are any candidates with this name
            if formatted_name in name_to_candidates:
                candidates = name_to_candidates[formatted_name]
                print(f"WARNING: {player['name']} ({position}) - no exact match")
                print(f"  Candidates: {candidates}")
            unmatched.append(f"{player['name']} ({position})")
    
    print(f"\nMatched {matched} players with IDs")
    print(f"Fixed {fixed} incorrect IDs")
    print(f"Unmatched: {len(unmatched)} players")
    
    if unmatched:
        print("\nUnmatched players:")
        for name in unmatched[:10]:  # Show first 10
            print(f"  - {name}")
        if len(unmatched) > 10:
            print(f"  ... and {len(unmatched) - 10} more")
    
    # Save updated data
    save_players_2025(players_data)
    print(f"\nUpdated src/data/players_2025.json with corrected player IDs")

if __name__ == "__main__":
    main()