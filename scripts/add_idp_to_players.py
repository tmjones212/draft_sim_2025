#!/usr/bin/env python3
import json
import os

def load_idp_players():
    """Load top DB and LB players from custom scoring stats"""
    script_dir = os.path.dirname(__file__)
    
    # Load DB and LB stats
    db_file = os.path.join(script_dir, 'custom_scoring_db_stats_2024.json')
    lb_file = os.path.join(script_dir, 'custom_scoring_lb_stats_2024.json')
    
    idp_players = []
    
    # Load DBs
    if os.path.exists(db_file):
        with open(db_file, 'r') as f:
            db_data = json.load(f)
            
        # Get top 40 DBs by 2024 points
        db_list = []
        for pid, pdata in db_data.items():
            if pdata.get('custom_season_total', 0) > 0:
                db_list.append({
                    'name': pdata['player_name'],
                    'position': 'DB',
                    'team': pdata.get('team'),
                    'points': pdata.get('custom_season_total', 0),
                    'games': pdata.get('games_played', 0)
                })
        
        # Sort by points and take top 40
        db_list.sort(key=lambda x: x['points'], reverse=True)
        for i, player in enumerate(db_list[:40], 1):
            idp_players.append({
                'position': 'DB',
                'team': player['team'] or 'FA',
                'rank': 200 + i,  # Start DB rankings at 201
                'name': player['name'],
                'adp': 200 + i + (i * 0.5)  # Spread out ADP values
            })
            print(f"DB{i}: {player['name']} - {player['points']:.1f} pts in {player['games']} games")
    
    # Load LBs
    if os.path.exists(lb_file):
        with open(lb_file, 'r') as f:
            lb_data = json.load(f)
            
        # Get top 40 LBs by 2024 points
        lb_list = []
        for pid, pdata in lb_data.items():
            if pdata.get('custom_season_total', 0) > 0:
                lb_list.append({
                    'name': pdata['player_name'],
                    'position': 'LB',
                    'team': pdata.get('team'),
                    'points': pdata.get('custom_season_total', 0),
                    'games': pdata.get('games_played', 0)
                })
        
        # Sort by points and take top 40
        lb_list.sort(key=lambda x: x['points'], reverse=True)
        for i, player in enumerate(lb_list[:40], 1):
            idp_players.append({
                'position': 'LB',
                'team': player['team'] or 'FA',
                'rank': 240 + i,  # Start LB rankings at 241
                'name': player['name'],
                'adp': 240 + i + (i * 0.5)  # Spread out ADP values
            })
            print(f"LB{i}: {player['name']} - {player['points']:.1f} pts in {player['games']} games")
    
    return idp_players

def update_players_file():
    """Update the players_2025.json file with IDP players"""
    script_dir = os.path.dirname(__file__)
    players_file = os.path.join(script_dir, '..', 'src', 'data', 'players_2025.json')
    
    # Load existing players
    with open(players_file, 'r') as f:
        data = json.load(f)
    
    # Get IDP players
    idp_players = load_idp_players()
    
    # Add IDP players to the list
    data['players'].extend(idp_players)
    
    # Save updated file
    with open(players_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\nAdded {len(idp_players)} IDP players to {players_file}")
    print(f"Total players: {len(data['players'])}")

if __name__ == "__main__":
    update_players_file()