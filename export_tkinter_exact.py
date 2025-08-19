#!/usr/bin/env python3
"""
Export EXACT player list as tkinter sees it
"""

import json
import sys
import os

# Add src to path like tkinter does
sys.path.insert(0, os.path.dirname(__file__))

# Import the SAME functions tkinter uses
from src.utils.player_generator import generate_mock_players
from src.utils.player_extensions import format_name
from src.services.custom_adp_manager import CustomADPManager

# Generate players EXACTLY like tkinter does
print("Generating players like tkinter...")
players = generate_mock_players()
print(f"Generated {len(players)} players")

# Apply custom ADP EXACTLY like tkinter does
adp_manager = CustomADPManager()
adp_manager.apply_custom_adp_to_players(players)
print(f"Applied {len(adp_manager.custom_adp_values)} custom ADP values")

# Sort by ADP like tkinter does
players.sort(key=lambda p: p.adp if p.adp else 999)

# Convert to JSON format for web
output_players = []
for p in players:
    output_players.append({
        'player_id': p.player_id,
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
        'var': getattr(p, 'var', 0)
    })

# Check specific players
print("\nVerification:")
for p in output_players:
    if p['name'] in ['Rashee Rice', 'Demario Douglas', 'DeMario Douglas', 'Pierre Strong', 'Dameon Pierce']:
        print(f"  {p['name']}: ADP {p['adp']}")

# Count by position
pos_counts = {}
for p in output_players:
    pos = p['position']
    pos_counts[pos] = pos_counts.get(pos, 0) + 1
print(f"\nPosition counts: {pos_counts}")

# Save to web_static
output = {'players': output_players}
with open('web_static/players_data.json', 'w') as f:
    json.dump(output, f, indent=2)

print(f"\nSaved {len(output_players)} players to web_static/players_data.json")
print("This should EXACTLY match what tkinter shows!")