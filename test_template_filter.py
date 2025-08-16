#!/usr/bin/env python3
"""Test template filtering logic"""

from src.core.template_manager import TemplateManager, DraftTemplate

# Create a test template with some draft picks
template = DraftTemplate("Test Template")
template.draft_results = [
    {"pick_number": 1, "round": 1, "pick_in_round": 1, "team_id": 1, "player_id": "7564"},  # Ja'Marr Chase
    {"pick_number": 2, "round": 1, "pick_in_round": 2, "team_id": 2, "player_id": "9509"},  # Bijan Robinson
    {"pick_number": 3, "round": 1, "pick_in_round": 3, "team_id": 3, "player_id": "6794"},  # Justin Jefferson
]

# Test player class
class TestPlayer:
    def __init__(self, name, player_id):
        self.name = name
        self.player_id = player_id

# Test filtering
test_players = [
    TestPlayer("Ja'Marr Chase", "7564"),  # Should find
    TestPlayer("Bijan Robinson", "9509"),  # Should find  
    TestPlayer("Josh Allen", "1234"),     # Should not find
]

for player in test_players:
    # Check if player was drafted
    player_found = False
    target_id = str(player.player_id)
    
    for pick in template.draft_results:
        if pick.get('player_id'):
            if str(pick['player_id']) == target_id:
                player_found = True
                break
    
    print(f"{player.name} (ID: {player.player_id}): {'FOUND' if player_found else 'NOT FOUND'}")

print("\nDraft results player IDs:", [pick.get('player_id') for pick in template.draft_results])