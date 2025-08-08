#!/usr/bin/env python3
"""Simple test for draft history functionality"""

import json
import os
from datetime import datetime
import shutil

# Test the draft history file operations directly
def test_draft_history():
    test_dir = "data/test_draft_history"
    
    # Clean and create directory
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)
    
    print("Testing Draft History File Operations")
    print("=" * 50)
    
    # Create a draft file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    draft_id = f"draft_{timestamp}"
    
    draft_data = {
        "id": draft_id,
        "name": "Test Draft 2025",
        "created": datetime.now().isoformat(),
        "modified": datetime.now().isoformat(),
        "picks": [],
        "user_team_id": 1,
        "manual_mode": False,
        "teams": {
            "1": {"name": "My Team", "draft_position": 1},
            "2": {"name": "Team 2", "draft_position": 2}
        },
        "config": {
            "num_teams": 10,
            "roster_spots": 17,
            "draft_type": "snake",
            "reversal_round": 3
        }
    }
    
    # Save draft file
    filepath = os.path.join(test_dir, f"{draft_id}.json")
    with open(filepath, 'w') as f:
        json.dump(draft_data, f, indent=2)
    print(f"✓ Created draft file: {draft_id}")
    
    # Add some picks
    pick1 = {
        "pick_number": 1,
        "round": 1,
        "pick_in_round": 1,
        "team_id": 1,
        "player": {
            "name": "Player One",
            "position": "RB",
            "team": "DAL",
            "adp": 5.0,
            "player_id": "p1"
        },
        "timestamp": datetime.now().isoformat()
    }
    
    draft_data["picks"].append(pick1)
    draft_data["modified"] = datetime.now().isoformat()
    
    # Save updated draft
    with open(filepath, 'w') as f:
        json.dump(draft_data, f, indent=2)
    print("✓ Added pick to draft")
    
    # Read draft back
    with open(filepath, 'r') as f:
        loaded_data = json.load(f)
    
    print(f"✓ Loaded draft: {loaded_data['name']}")
    print(f"  - Picks: {len(loaded_data['picks'])}")
    print(f"  - Teams: {len(loaded_data['teams'])}")
    
    # List all drafts
    drafts = []
    for filename in os.listdir(test_dir):
        if filename.endswith('.json'):
            filepath = os.path.join(test_dir, filename)
            with open(filepath, 'r') as f:
                data = json.load(f)
                drafts.append({
                    "id": data.get("id"),
                    "name": data.get("name"),
                    "picks": len(data.get("picks", []))
                })
    
    print(f"✓ Found {len(drafts)} draft(s):")
    for draft in drafts:
        print(f"  - {draft['name']} ({draft['picks']} picks)")
    
    print("\n✅ All file operations work correctly!")
    
    # Clean up
    shutil.rmtree(test_dir)
    print("✓ Cleaned up test files")

if __name__ == "__main__":
    test_draft_history()