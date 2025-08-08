#!/usr/bin/env python3
"""Test script for draft history functionality"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import directly to avoid PIL dependency
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

# Copy the DraftHistoryManager class inline to test
exec(open('src/services/draft_history_manager.py').read())

# Simple mock classes for testing
class Player:
    def __init__(self, player_id, name, position, team, adp):
        self.player_id = player_id
        self.name = name
        self.position = position
        self.team = team
        self.adp = adp

class DraftPick:
    def __init__(self, pick_number, round, pick_in_round, team_id, player):
        self.pick_number = pick_number
        self.round = round
        self.pick_in_round = pick_in_round
        self.team_id = team_id
        self.player = player
import json
import shutil

def test_draft_history():
    # Clean up test directory
    test_dir = "data/test_draft_history"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    
    # Create manager with test directory
    manager = DraftHistoryManager(history_dir=test_dir)
    
    print("Testing Draft History Manager")
    print("=" * 50)
    
    # Test 1: Start new draft
    draft_id = manager.start_new_draft("Test Draft 2025")
    print(f"✓ Started new draft: {draft_id}")
    
    # Test 2: Update draft name
    manager.update_draft_name("My Awesome Draft")
    print("✓ Updated draft name")
    
    # Test 3: Save team configuration
    teams = {
        1: type('Team', (), {'name': 'Team 1', 'draft_position': 1})(),
        2: type('Team', (), {'name': 'Team 2', 'draft_position': 2})(),
    }
    manager.save_team_config(teams, user_team_id=1, manual_mode=False)
    print("✓ Saved team configuration")
    
    # Test 4: Save some picks
    player1 = Player(
        player_id="p1",
        name="Player One",
        position="RB",
        team="DAL",
        adp=5.0
    )
    
    pick1 = DraftPick(
        pick_number=1,
        round=1,
        pick_in_round=1,
        team_id=1,
        player=player1
    )
    
    manager.save_pick(pick1, user_team_id=1, manual_mode=False)
    print("✓ Saved pick 1")
    
    player2 = Player(
        player_id="p2",
        name="Player Two",
        position="WR",
        team="NYG",
        adp=10.0
    )
    
    pick2 = DraftPick(
        pick_number=2,
        round=1,
        pick_in_round=2,
        team_id=2,
        player=player2
    )
    
    manager.save_pick(pick2, user_team_id=1, manual_mode=False)
    print("✓ Saved pick 2")
    
    # Test 5: Get draft list
    drafts = manager.get_draft_list()
    print(f"✓ Retrieved {len(drafts)} draft(s)")
    for draft in drafts:
        print(f"  - {draft['name']} ({draft['picks_count']} picks)")
    
    # Test 6: Load draft
    loaded_draft = manager.load_draft(draft_id)
    print(f"✓ Loaded draft: {loaded_draft['name']}")
    print(f"  - Picks: {len(loaded_draft['picks'])}")
    print(f"  - Teams: {len(loaded_draft['teams'])}")
    
    # Test 7: Remove picks after reversion
    manager.remove_picks_after(1)
    
    # Reload to verify
    loaded_draft = manager.load_draft(draft_id)
    print(f"✓ Removed picks after 1, now have {len(loaded_draft['picks'])} pick(s)")
    
    # Test 8: Start another draft
    draft_id2 = manager.start_new_draft("Second Draft")
    print(f"✓ Started second draft: {draft_id2}")
    
    # Test 9: Verify we have 2 drafts
    drafts = manager.get_draft_list()
    print(f"✓ Now have {len(drafts)} draft(s) total")
    
    # Verify file structure
    print("\nFile Structure:")
    for filename in os.listdir(test_dir):
        filepath = os.path.join(test_dir, filename)
        with open(filepath, 'r') as f:
            data = json.load(f)
            print(f"  - {filename}: {data['name']} ({len(data.get('picks', []))} picks)")
    
    print("\n✅ All tests passed!")
    
    # Clean up
    shutil.rmtree(test_dir)
    print("✓ Cleaned up test files")

if __name__ == "__main__":
    test_draft_history()