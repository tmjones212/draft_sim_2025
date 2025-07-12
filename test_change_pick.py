#!/usr/bin/env python3
"""Test script for the change pick functionality"""

import os
import sys
import time

# Add the current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from main import MockDraftApp
import tkinter as tk


def test_change_pick():
    """Test changing a pick to a player drafted later"""
    print("Starting change pick test...")
    
    # Create the app
    root = tk.Tk()
    app = MockDraftApp(root)
    
    # Wait for players to load
    print("Waiting for players to load...")
    while not app.players_loaded:
        root.update()
        time.sleep(0.1)
    
    print(f"Loaded {len(app.all_players)} players")
    
    # Select a team (team 5)
    print("\nSelecting team 5...")
    app.on_team_selected(5)
    
    # Let the draft run to pick 15
    print("\nAuto-drafting to pick 15...")
    while len(app.draft_engine.draft_results) < 15:
        root.update()
        time.sleep(0.05)
    
    # Print current draft results
    print("\nDraft results before change:")
    for i, pick in enumerate(app.draft_engine.draft_results[:15]):
        print(f"Pick {i+1}: {pick.player.name} to Team {pick.team_id}")
    
    # Find who was picked at pick 10 and pick 13
    pick_10_player = app.draft_engine.draft_results[9].player  # 0-based index
    pick_13_player = app.draft_engine.draft_results[12].player
    
    print(f"\nPick 10: {pick_10_player.name}")
    print(f"Pick 13: {pick_13_player.name}")
    
    # Change pick 10 to the player drafted at pick 13
    print(f"\nChanging pick 10 from {pick_10_player.name} to {pick_13_player.name}...")
    app.on_pick_changed(10, pick_13_player)
    
    # Let the app process
    for _ in range(10):
        root.update()
        time.sleep(0.1)
    
    # Check results
    print("\nDraft results after change:")
    current_picks = len(app.draft_engine.draft_results)
    for i, pick in enumerate(app.draft_engine.draft_results[:min(current_picks, 20)]):
        print(f"Pick {i+1}: {pick.player.name} to Team {pick.team_id}")
    
    # Verify the change worked
    new_pick_10 = app.draft_engine.draft_results[9].player
    if new_pick_10.player_id == pick_13_player.player_id:
        print(f"\n✓ SUCCESS: Pick 10 is now {new_pick_10.name}")
    else:
        print(f"\n✗ FAILED: Pick 10 is {new_pick_10.name}, expected {pick_13_player.name}")
    
    # Check for duplicates
    print("\nChecking for duplicate players...")
    drafted_players = {}
    duplicates = []
    
    for i, pick in enumerate(app.draft_engine.draft_results):
        player_id = pick.player.player_id
        if player_id in drafted_players:
            duplicates.append(f"{pick.player.name} drafted at picks {drafted_players[player_id]+1} and {i+1}")
        else:
            drafted_players[player_id] = i
    
    if duplicates:
        print("✗ DUPLICATES FOUND:")
        for dup in duplicates:
            print(f"  - {dup}")
    else:
        print("✓ No duplicate players found")
    
    # Check if the original pick 10 player is available or drafted elsewhere
    original_available = pick_10_player in app.available_players
    original_drafted_at = None
    for i, pick in enumerate(app.draft_engine.draft_results):
        if pick.player.player_id == pick_10_player.player_id:
            original_drafted_at = i + 1
            break
    
    if original_available:
        print(f"\n✓ {pick_10_player.name} is now available to be drafted")
    elif original_drafted_at:
        print(f"\n✓ {pick_10_player.name} was drafted at pick {original_drafted_at}")
    else:
        print(f"\n✗ ERROR: {pick_10_player.name} is neither available nor drafted!")
    
    # Clean up
    root.destroy()
    print("\nTest complete!")


if __name__ == "__main__":
    test_change_pick()