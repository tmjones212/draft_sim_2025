#!/usr/bin/env python3
"""
Regenerate players_data.json for offline website with ALL positions
"""

import json
import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(__file__))

from src.utils.player_data_fetcher import get_players_with_fallback
from src.utils.player_extensions import format_name

# Get players with LB/DB included (same as tkinter)
print("Getting players with all positions...")
players = get_players_with_fallback()
print(f"Got {len(players)} total players")

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
        # Format name for display
        player['name'] = format_name(player['name'])
        
print(f"Updated {updated} players with custom ADP")

# Format all names and ensure ID field exists
for player in players:
    player['name'] = format_name(player['name'])
    # Ensure 'id' field exists (JavaScript expects 'id', not 'player_id')
    if 'player_id' in player and 'id' not in player:
        player['id'] = player['player_id']

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