#!/usr/bin/env python3
"""
Regenerate players_data.json for the offline website with custom ADP values applied
"""

import json
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.nfc_adp_fetcher import NFCADPFetcher
from src.utils.player_extensions import format_name
from src.utils.player_data_fetcher import load_projections

def calculate_var(players, projections, num_teams=10):
    """Calculate Value Above Replacement for each player using projected points"""
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
            # Add projection points to player
            formatted_name = format_name(player['name'])
            if formatted_name in projections:
                player['points_2025_proj'] = projections[formatted_name]
            elif player['name'] in projections:
                player['points_2025_proj'] = projections[player['name']]
            else:
                # Estimate based on ADP if no projection
                # Top players get ~300 points, decreasing by ADP
                adp = player.get('adp', 999)
                if adp < 300:
                    player['points_2025_proj'] = max(50, 350 - (adp * 1.0))
                else:
                    player['points_2025_proj'] = 50
            
            position_groups[pos].append(player)
    
    # Calculate VAR for each position using projected points
    for position, group in position_groups.items():
        # Sort by projected points (descending)
        sorted_players = sorted(group, key=lambda p: p.get('points_2025_proj', 0), reverse=True)
        
        # Find replacement level points
        replacement_rank = replacement_levels.get(position, 10)
        replacement_points = 0
        
        if len(sorted_players) >= replacement_rank:
            replacement_points = sorted_players[replacement_rank - 1].get('points_2025_proj', 0)
        elif sorted_players:
            # If we don't have enough players, use the last one
            replacement_points = sorted_players[-1].get('points_2025_proj', 0)
        
        # Calculate VAR for each player
        for player in group:
            proj_points = player.get('points_2025_proj', 0)
            player['var'] = round(proj_points - replacement_points, 1)

def main():
    # Load base players from src
    with open('src/data/players_2025.json', 'r') as f:
        data = json.load(f)
        players = data.get('players', data)
    
    # Load custom ADP values
    with open('data/custom_adp.json', 'r') as f:
        custom_adp = json.load(f)
    
    # Load NFC ADP data
    nfc_fetcher = NFCADPFetcher()
    nfc_adp_data = nfc_fetcher.load_nfc_adp()
    
    # Load projection data
    projections = load_projections()
    
    print(f"Loaded {len(players)} players")
    print(f"Loaded {len(custom_adp)} custom ADP values")
    print(f"Loaded {len(nfc_adp_data)} NFC ADP values")
    print(f"Loaded {len(projections)} player projections")
    
    # Apply custom ADP values and NFC ADP to players
    updated_count = 0
    nfc_count = 0
    rashee_found = False
    for player in players:
        # Apply custom ADP
        player_id = player.get('player_id')
        if player_id and player_id in custom_adp:
            original_adp = player.get('adp', 999)
            player['adp'] = custom_adp[player_id]
            updated_count += 1
            
            if player.get('name') == 'Rashee Rice':
                rashee_found = True
                print(f"Updated Rashee Rice ADP: {original_adp} -> {custom_adp[player_id]}")
        
        # Apply NFC ADP
        player_name = player.get('name')
        if player_name:
            formatted_name = format_name(player_name)
            if formatted_name in nfc_adp_data:
                player['nfc_adp'] = nfc_adp_data[formatted_name]
                nfc_count += 1
    
    if not rashee_found:
        # Check if Rashee exists at all
        for player in players:
            if 'Rashee' in player.get('name', ''):
                print(f"Found player: {player.get('name')} with ID {player.get('player_id')}")
    
    print(f"Updated {updated_count} players with custom ADP values")
    print(f"Added NFC ADP to {nfc_count} players")
    
    # Calculate VAR for all players using projections
    calculate_var(players, projections)
    print(f"Calculated VAR for all players using projected points")
    
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