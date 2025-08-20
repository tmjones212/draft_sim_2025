#!/usr/bin/env python3
"""
Regenerate players_data.json for the offline website with custom ADP values applied
"""

import json
import os

def calculate_var(players, num_teams=10):
    """Calculate Value Above Replacement for each player using ADP-based approach"""
    # Define replacement level for each position in a 10-team league
    replacement_levels = {
        'QB': 20,    # 2 QBs per team = 20th QB
        'RB': 22,    # 2.2 RBs per team (with flex) = 22nd RB
        'WR': 38,    # 3.8 WRs per team (with flex) = 38th WR
        'TE': 10,    # 1 TE per team = 10th TE
        'LB': 30,    # 3 LBs per team = 30th LB
        'DB': 30,    # 3 DBs per team = 30th DB
        'K': 10,     # 1 K per team = 10th K
        'DST': 10    # 1 DST per team = 10th DST
    }
    
    # Group players by position
    position_groups = {}
    
    for player in players:
        pos = player.get('position')
        if pos:
            if pos not in position_groups:
                position_groups[pos] = []
            position_groups[pos].append(player)
    
    # Calculate VAR for each position using ADP-based approach
    for position, group in position_groups.items():
        # Sort by ADP (ascending - lower ADP is better)
        sorted_players = sorted(group, key=lambda p: p.get('adp', 999))
        
        # Find replacement level based on position rank
        replacement_rank = replacement_levels.get(position, 10)
        
        # Assign VAR based on position rank
        for idx, player in enumerate(sorted_players):
            # Calculate VAR as inverse of position rank relative to replacement
            # Higher ranked players get higher VAR
            if idx < replacement_rank:
                # Players above replacement level get positive VAR
                # Scale from 100 (best) down to 1 at replacement level
                var_value = round(100 * (replacement_rank - idx) / replacement_rank, 1)
            else:
                # Players below replacement get negative or zero VAR
                var_value = round(-5 * (idx - replacement_rank + 1), 1)
            
            player['var'] = var_value

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
    
    # Calculate VAR for all players
    calculate_var(players)
    print(f"Calculated VAR for all players")
    
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