#!/usr/bin/env python3
import json
import os

def add_better_idp_players():
    """Add a more comprehensive list of IDP players with realistic rankings"""
    script_dir = os.path.dirname(__file__)
    players_file = os.path.join(script_dir, '..', 'src', 'data', 'players_2025.json')
    
    # Load existing players
    with open(players_file, 'r') as f:
        data = json.load(f)
    
    # Remove any existing DB/LB players
    data['players'] = [p for p in data['players'] if p['position'] not in ['DB', 'LB']]
    
    # Top DBs for 2025 fantasy (mix of safeties and corners)
    top_dbs = [
        # Top tier safeties (usually score more in IDP)
        {"name": "Antoine Winfield Jr.", "team": "TB"},
        {"name": "Jessie Bates III", "team": "ATL"},
        {"name": "Kyle Hamilton", "team": "BAL"},
        {"name": "Derwin James", "team": "LAC"},
        {"name": "Budda Baker", "team": "ARI"},
        {"name": "Minkah Fitzpatrick", "team": "PIT"},
        {"name": "Talanoa Hufanga", "team": "SF"},
        {"name": "Nick Cross", "team": "IND"},  # Specifically requested
        {"name": "Jevon Holland", "team": "MIA"},
        {"name": "Marcus Williams", "team": "BAL"},
        
        # Mid-tier safeties
        {"name": "Jordan Poyer", "team": "MIA"},
        {"name": "Kevin Byard", "team": "CHI"},
        {"name": "Kamren Curl", "team": "LAR"},
        {"name": "Jalen Pitre", "team": "HOU"},
        {"name": "Julian Love", "team": "SEA"},
        
        # Some corners that tackle well
        {"name": "Sauce Gardner", "team": "NYJ"},
        {"name": "Patrick Surtain II", "team": "DEN"},
        {"name": "Jalen Ramsey", "team": "MIA"},
        {"name": "L'Jarius Sneed", "team": "KC"},
        {"name": "DaRon Bland", "team": "DAL"},
    ]
    
    # Top LBs for 2025 fantasy
    top_lbs = [
        # Elite tier
        {"name": "Roquan Smith", "team": "BAL"},
        {"name": "Fred Warner", "team": "SF"},
        {"name": "Foyesade Oluokun", "team": "JAX"},
        {"name": "T.J. Watt", "team": "PIT"},
        {"name": "Nick Bolton", "team": "KC"},
        
        # Second tier
        {"name": "Dre Greenlaw", "team": "SF"},
        {"name": "Patrick Queen", "team": "PIT"},
        {"name": "Zaire Franklin", "team": "IND"},
        {"name": "Bobby Wagner", "team": "WAS"},
        {"name": "Lavonte David", "team": "TB"},
        
        # Third tier
        {"name": "Ernest Jones", "team": "SEA"},
        {"name": "Quincy Williams", "team": "NYJ"},
        {"name": "Jordyn Brooks", "team": "MIA"},
        {"name": "Alex Singleton", "team": "DEN"},
        {"name": "Divine Deablo", "team": "LV"},
        
        # More options
        {"name": "Kaden Elliss", "team": "ATL"},
        {"name": "Jerome Baker", "team": "TEN"},
        {"name": "Logan Wilson", "team": "CIN"},
        {"name": "Matt Milano", "team": "BUF"},
        {"name": "Tremaine Edmunds", "team": "CHI"},
    ]
    
    # Add DBs starting at rank 161
    start_rank = len(data['players']) + 1
    for i, db in enumerate(top_dbs):
        data['players'].append({
            'position': 'DB',
            'team': db['team'],
            'rank': start_rank + i,
            'name': db['name'],
            'adp': 160 + (i * 2.5)  # Spread out ADP values
        })
    
    # Add LBs
    start_rank = len(data['players']) + 1
    for i, lb in enumerate(top_lbs):
        data['players'].append({
            'position': 'LB',
            'team': lb['team'],
            'rank': start_rank + i,
            'name': lb['name'],
            'adp': 165 + (i * 2.5)  # Slightly higher ADP than DBs
        })
    
    # Save updated file
    with open(players_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    db_count = len(top_dbs)
    lb_count = len(top_lbs)
    print(f"Added {db_count} DB players and {lb_count} LB players")
    print(f"Total players: {len(data['players'])}")
    print(f"\nNick Cross has been specifically included in the DB list")

if __name__ == "__main__":
    add_better_idp_players()