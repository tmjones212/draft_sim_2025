#!/usr/bin/env python3
"""
Regenerate players_data.json for the offline website with custom ADP values applied
"""

import json
import os

def main():
    # Load base players from src
    with open('src/data/players_2025.json', 'r') as f:
        data = json.load(f)
        players = data.get('players', data)
    
    # Load custom ADP values
    with open('data/custom_adp.json', 'r') as f:
        custom_adp = json.load(f)
    
    print(f"Loaded {len(players)} players")
    print(f"Loaded {len(custom_adp)} custom ADP values")
    
    # Apply custom ADP values to players
    updated_count = 0
    rashee_found = False
    for player in players:
        player_id = player.get('player_id')
        if player_id and player_id in custom_adp:
            original_adp = player.get('adp', 999)
            player['adp'] = custom_adp[player_id]
            updated_count += 1
            
            if player.get('name') == 'Rashee Rice':
                rashee_found = True
                print(f"Updated Rashee Rice ADP: {original_adp} -> {custom_adp[player_id]}")
    
    if not rashee_found:
        # Check if Rashee exists at all
        for player in players:
            if 'Rashee' in player.get('name', ''):
                print(f"Found player: {player.get('name')} with ID {player.get('player_id')}")
    
    print(f"Updated {updated_count} players with custom ADP values")
    
    # Sort by ADP
    players.sort(key=lambda p: p.get('adp', 999))
    
    # Create the output structure
    output = {
        'players': players
    }
    
    # Save to web_static
    output_path = 'web_static/players_data.json'
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"Saved {len(players)} players to {output_path}")
    
    # Verify Rashee Rice in output
    with open(output_path, 'r') as f:
        verify_data = json.load(f)
        for p in verify_data['players']:
            if p.get('name') == 'Rashee Rice':
                print(f"Verified: Rashee Rice has ADP {p.get('adp')} in output file")
                break

if __name__ == '__main__':
    main()