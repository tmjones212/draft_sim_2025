#!/usr/bin/env python3
"""
Regenerate players_data.json for offline website with ALL positions
"""

import json
import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(__file__))

from src.utils.player_generator import generate_mock_players
from src.utils.player_extensions import format_name

# Generate players EXACTLY like tkinter does (includes VAR calculation)
print("Getting players with all positions...")
player_objects = generate_mock_players()
print(f"Got {len(player_objects)} total players")

# Convert player objects to dictionaries
players = []
for p in player_objects:
    player_dict = {
        'player_id': p.player_id,
        'id': p.player_id,  # JavaScript expects 'id'
        'name': p.name,  # Already formatted by generate_mock_players
        'position': p.position,
        'team': p.team,
        'rank': p.rank,
        'adp': p.adp,
        'bye_week': p.bye_week,
        'position_rank_2024': getattr(p, 'position_rank_2024', None),
        'position_rank_proj': getattr(p, 'position_rank_proj', None),
        'points_2024': getattr(p, 'points_2024', None),
        'points_2025_proj': getattr(p, 'points_2025_proj', None),
        'var': getattr(p, 'var', 0)  # Include VAR!
    }
    players.append(player_dict)

# Count by position
pos_counts = {}
for p in players:
    pos = p.get('position', 'UNKNOWN')
    pos_counts[pos] = pos_counts.get(pos, 0) + 1
print(f"Position counts: {pos_counts}")

# Load custom ADP
with open('data/custom_adp.json', 'r') as f:
    custom_adp = json.load(f)
print(f"Loaded {len(custom_adp)} custom ADP values")

# Apply custom ADP values
updated = 0
for player in players:
    pid = str(player.get('player_id', ''))
    if pid in custom_adp:
        original = player.get('adp', 999)
        player['adp'] = custom_adp[pid]
        updated += 1
        
print(f"Updated {updated} players with custom ADP")

# Sort by ADP
players.sort(key=lambda p: p.get('adp', 999))

# Save to web_static
output = {'players': players}
with open('web_static/players_data.json', 'w') as f:
    json.dump(output, f, indent=2)

print(f"\nSaved {len(players)} players to web_static/players_data.json")

# Verify key players
print("\nVerification:")
for p in players:
    if p['name'] in ['Rashee Rice', 'Demario Douglas', 'Pierre Strong', 'Dameon Pierce', 'Joshua Palmer']:
        print(f"  {p['name']}: ADP {p.get('adp')}")