#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.player_generator import generate_mock_players

# Generate players like tkinter does (which calculates VAR)
players = generate_mock_players()
print(f'Generated {len(players)} players')

# Check VAR values
has_var = 0
no_var = 0
sample = []
for p in players:
    if hasattr(p, 'var') and p.var is not None:
        has_var += 1
    else:
        no_var += 1
    if len(sample) < 5:
        var_val = p.var if hasattr(p, 'var') else None
        proj_val = p.points_2025_proj if hasattr(p, 'points_2025_proj') else None
        sample.append(f'{p.name}: VAR={var_val}, Proj={proj_val}')

print(f'Players with VAR: {has_var}')
print(f'Players without VAR: {no_var}')
print('\nSample:')
for s in sample:
    print(f'  {s}')