#!/usr/bin/env python3
"""Verify forced picks and exclusions are configured correctly"""

import os
import json

# Check if preset file exists
preset_file = "data/draft_presets.json"

if os.path.exists(preset_file):
    with open(preset_file, 'r') as f:
        data = json.load(f)
    
    print("=== Draft Presets File Contents ===")
    print(json.dumps(data, indent=2))
    
    if "presets" in data and "Default League" in data["presets"]:
        preset = data["presets"]["Default League"]
        
        print("\n=== Default League Preset ===")
        print(f"Enabled: {preset.get('enabled', False)}")
        
        print("\n--- Player Exclusions ---")
        exclusions = preset.get('player_exclusions', [])
        if exclusions:
            for exc in exclusions:
                print(f"  {exc['team_name']}: Cannot draft {exc['player_name']}")
        else:
            print("  No exclusions found!")
        
        print("\n--- Forced Picks ---")
        forced = preset.get('forced_picks', [])
        if forced:
            for fp in forced:
                print(f"  {fp['team_name']}: Must draft {fp['player_name']} at pick #{fp['pick_number']}")
        else:
            print("  No forced picks found!")
    else:
        print("\nDefault League preset not found!")
else:
    print(f"Preset file does not exist at: {preset_file}")
    print("The file will be created when you run the application.")

print("\n=== Expected Configuration ===")
print("Exclusions:")
print("  Johnson: Cannot draft JOSH ALLEN")
print("  Johnson: Cannot draft BROCK BOWERS")
print("  Luan: Cannot draft BROCK BOWERS")
print("\nForced Picks:")
print("  Luan: Must draft NICO COLLINS at pick #10")

input("\nPress Enter to exit...")