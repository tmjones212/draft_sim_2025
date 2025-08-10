#!/usr/bin/env python3
"""Generate players_data.json for web static version using current ADP values"""

import json
from src.utils.player_generator import generate_mock_players

def main():
    # Generate players using the same logic as the Python app
    players = generate_mock_players()
    
    # Convert to JSON-serializable format
    players_data = []
    for player in players:
        player_dict = {
            'id': str(hash(player.name)),
            'name': player.name,
            'position': player.position,
            'team': player.team or '',
            'adp': float(player.adp) if player.adp else 999.0,
            'rank': player.rank,
            'projection': float(player.points_2025_proj) if player.points_2025_proj else 0.0,
            'bye_week': player.bye_week or 0,
            'var': float(player.var) if player.var else 0.0,
            'points_2024': float(player.points_2024) if player.points_2024 else 0.0
        }
        players_data.append(player_dict)
    
    # Sort by ADP
    players_data.sort(key=lambda x: x['adp'])
    
    # Save to JSON file
    output = {'players': players_data}
    with open('web_static/players_data.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"Generated web_static/players_data.json with {len(players_data)} players")
    
    # Show top 20 players for verification
    print("\nTop 20 players by ADP:")
    for i, p in enumerate(players_data[:20], 1):
        print(f"{i:2}. {p['name']:25} ({p['position']:3}) ADP: {p['adp']:5.1f}")

if __name__ == '__main__':
    main()