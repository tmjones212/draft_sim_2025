#!/usr/bin/env python3
"""
Regenerate players_data.json for offline website matching tkinter behavior
"""

import json

# Load base players
with open('src/data/players_2025.json', 'r') as f:
    all_players = json.load(f)['players']

# Load custom ADP
with open('data/custom_adp.json', 'r') as f:
    custom_adp = json.load(f)

print(f"Loaded {len(all_players)} total players (with duplicates)")
print(f"Loaded {len(custom_adp)} custom ADP values")

# DEDUPLICATE - Keep only first occurrence of each player_id (like tkinter does)
seen_ids = set()
players = []
skipped = []

for p in all_players:
    pid = p.get('player_id')
    if pid not in seen_ids:
        seen_ids.add(pid)
        players.append(p.copy())  # Make a copy to avoid modifying original
    else:
        skipped.append(f"{p['name']} (ID: {pid})")

print(f"After deduplication: {len(players)} unique players")
print(f"Skipped {len(skipped)} duplicate entries:")
for name in skipped[:10]:  # Show first 10
    print(f"  - {name}")

# Apply custom ADP values
updated = 0
for player in players:
    pid = player.get('player_id')
    if pid in custom_adp:
        original = player.get('adp', 999)
        player['adp'] = custom_adp[pid]
        updated += 1
        if player['name'] in ['Rashee Rice', 'Jameson Williams', 'Pierre Strong', 'Demario Douglas', 'Joshua Palmer']:
            print(f"Updated {player['name']}: {original} -> {player['adp']}")

print(f"Updated {updated} players with custom ADP")

# Sort by ADP
players.sort(key=lambda p: p.get('adp', 999))

# Save to web_static
output = {'players': players}
with open('web_static/players_data.json', 'w') as f:
    json.dump(output, f, indent=2)

print(f"\nSaved {len(players)} deduplicated players to web_static/players_data.json")

# Verify some key players
print("\nVerification:")
for p in players:
    if p['name'] in ['Rashee Rice', 'Jameson Williams', 'Joshua Palmer', 'Dameon Pierce']:
        print(f"  {p['name']}: ADP {p.get('adp')}")