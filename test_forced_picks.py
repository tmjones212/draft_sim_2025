#!/usr/bin/env python3
"""Test script to verify forced picks and exclusions work correctly"""

from src.services.draft_preset_manager import DraftPresetManager
from src.models.draft_preset import DraftPreset, PlayerExclusion, ForcedPick

# Create and test the preset manager
preset_manager = DraftPresetManager()

# Create the default preset (or get existing one)
preset_manager.create_default_preset()

# Get the active preset
preset = preset_manager.get_active_preset()

if preset:
    print("Active preset found: Default League")
    print(f"Enabled: {preset.enabled}")
    print(f"Draft order: {preset.draft_order}")
    print(f"User position: {preset.user_position} ({preset.draft_order[preset.user_position]})")
    
    print("\n--- Player Exclusions ---")
    for exc in preset.player_exclusions:
        print(f"  {exc.team_name}: Cannot draft {exc.player_name} (enabled: {exc.enabled})")
    
    print("\n--- Forced Picks ---")
    for fp in preset.forced_picks:
        print(f"  {fp.team_name}: Must draft {fp.player_name} at pick #{fp.pick_number} (enabled: {fp.enabled})")
    
    # Test the methods
    print("\n--- Testing Methods ---")
    
    # Test exclusion check
    print(f"Is Josh Allen excluded for Johnson? {preset.is_player_excluded('Johnson', 'JOSH ALLEN')}")
    print(f"Is Brock Bowers excluded for Johnson? {preset.is_player_excluded('Johnson', 'BROCK BOWERS')}")
    print(f"Is Brock Bowers excluded for Luan? {preset.is_player_excluded('Luan', 'BROCK BOWERS')}")
    print(f"Is Josh Allen excluded for Luan? {preset.is_player_excluded('Luan', 'JOSH ALLEN')}")
    
    # Test forced pick
    print(f"\nForced pick for Luan at pick 10: {preset.get_forced_pick('Luan', 10)}")
    print(f"Forced pick for Johnson at pick 10: {preset.get_forced_pick('Johnson', 10)}")
    print(f"Forced pick for Luan at pick 20: {preset.get_forced_pick('Luan', 20)}")
    
else:
    print("No active preset found")

print("\n--- Simulating Draft Logic ---")
# Test with mock players
from src.utils.player_generator import generate_mock_players
players = generate_mock_players()

# Find specific players
nico_collins = None
josh_allen = None  
brock_bowers = None

for p in players:
    if "NICO COLLINS" in p.name.upper():
        nico_collins = p
    elif "JOSH ALLEN" in p.name.upper():
        josh_allen = p
    elif "BROCK BOWERS" in p.name.upper():
        brock_bowers = p

print(f"\nNico Collins found: {nico_collins.name if nico_collins else 'NOT FOUND'}")
print(f"Josh Allen found: {josh_allen.name if josh_allen else 'NOT FOUND'}")
print(f"Brock Bowers found: {brock_bowers.name if brock_bowers else 'NOT FOUND'}")