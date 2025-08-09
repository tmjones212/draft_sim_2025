#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/alaba/mock_sim_2025')

from src.services.sos_manager import SOSManager
import json

# Load SOS manager
sos_manager = SOSManager()

print("SOS Data loaded:")
print(f"Number of teams in SOS data: {len(sos_manager.sos_data)}")
print(f"Teams in SOS data: {sorted(sos_manager.sos_data.keys())}")
print()

# Load player data to test
with open('src/data/players_2025.json', 'r') as f:
    data = json.load(f)
    players = data.get('players', [])

# Test first 10 players
print("Testing first 10 players:")
for i, player in enumerate(players[:10]):
    name = player.get('name', 'Unknown')
    team = player.get('team', 'No team')
    position = player.get('position', 'No position')
    
    sos = sos_manager.get_sos(team, position)
    sos_display = sos_manager.get_sos_display(team, position)
    
    print(f"{i+1}. {name} ({position}, {team})")
    print(f"   SOS value: {sos}")
    print(f"   SOS display: '{sos_display}'")
    print()

# Test specific mapping cases
print("\nTesting team mappings:")
test_cases = [
    ('ARZ', 'QB'),
    ('ARI', 'QB'),
    ('LA', 'RB'),
    ('LAR', 'RB'),
    ('CIN', 'WR'),
    ('KC', 'QB'),
]

for team, pos in test_cases:
    sos = sos_manager.get_sos(team, pos)
    print(f"{team} {pos}: SOS = {sos}")