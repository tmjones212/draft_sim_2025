#!/usr/bin/env python3
"""Test script for draft pick trades functionality"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.services.draft_trade_service import DraftTradeService
from src.services.draft_order_service import DraftOrderService
from src.core.draft_logic import DraftEngine
import config

def test_trade_service():
    """Test the basic trade service functionality"""
    print("Testing Trade Service...")
    
    # Create trade service
    trade_service = DraftTradeService()
    
    # Add the example trade: Team 8 trades 1st & 4th for Team 7's 2nd & 3rd
    trade_service.add_trade(8, [1, 4], 7, [2, 3])
    
    # Check the trades were recorded
    print("Trades Summary:")
    for summary in trade_service.get_trades_summary():
        print(f"  {summary}")
    
    # Test pick ownership
    print("\nPick Ownership After Trade:")
    print(f"  Team 8's 1st round pick now owned by: Team {trade_service.get_pick_owner(8, 1)}")
    print(f"  Team 8's 4th round pick now owned by: Team {trade_service.get_pick_owner(8, 4)}")
    print(f"  Team 7's 2nd round pick now owned by: Team {trade_service.get_pick_owner(7, 2)}")
    print(f"  Team 7's 3rd round pick now owned by: Team {trade_service.get_pick_owner(7, 3)}")
    print(f"  Team 8's 5th round pick (not traded) owned by: Team {trade_service.get_pick_owner(8, 5)}")
    
    return trade_service

def test_draft_order_with_trades():
    """Test the draft order service with trades"""
    print("\n\nTesting Draft Order Service with Trades...")
    
    # Create services
    trade_service = DraftTradeService()
    trade_service.add_trade(8, [1, 4], 7, [2, 3])
    
    draft_order_service = DraftOrderService(
        num_teams=config.num_teams,
        reversal_round=config.reversal_round,
        trade_service=trade_service
    )
    
    # Test specific picks
    test_picks = [
        (8, "Team 8's 1st round pick"),   # Pick 8 in round 1
        (17, "Team 7's 2nd round pick"),   # Pick 17 in round 2 (reverse order)
        (27, "Team 7's 3rd round pick"),   # Pick 27 in round 3 (same as round 2)
        (38, "Team 8's 4th round pick"),   # Pick 38 in round 4
    ]
    
    print("\nPick Analysis:")
    for pick_num, description in test_picks:
        round_num, pick_in_round, team_id = draft_order_service.get_pick_info(pick_num, 18)
        print(f"  Pick #{pick_num} ({description}):")
        print(f"    Round {round_num}, Pick {pick_in_round} → Team {team_id}")

def test_draft_engine_with_trades():
    """Test the draft engine with trades"""
    print("\n\nTesting Draft Engine with Trades...")
    
    # Create services
    trade_service = DraftTradeService()
    trade_service.add_trade(8, [1, 4], 7, [2, 3])
    
    # Create draft engine
    draft_engine = DraftEngine(
        num_teams=config.num_teams,
        roster_spots=config.roster_spots,
        draft_type=config.draft_type,
        reversal_round=config.reversal_round,
        trade_service=trade_service
    )
    
    # Simulate picks through the first 4 rounds
    print("\nFirst 40 picks with trades applied:")
    for i in range(40):
        pick_num, round_num, pick_in_round, team_on_clock = draft_engine.get_current_pick_info()
        if pick_num == 0:
            break
        
        # Highlight traded picks
        marker = ""
        if pick_num in [8, 17, 27, 38]:  # The traded picks
            marker = " ← TRADED"
        
        print(f"  Pick #{pick_num}: Round {round_num}.{pick_in_round} → Team {team_on_clock}{marker}")
        
        # Simulate making a pick (just to advance)
        from src.models import Team, Player
        team = Team(team_on_clock, f"Team {team_on_clock}")
        player = Player(f"Player{pick_num}", "QB", f"Team{pick_num}")
        draft_engine.make_pick(team, player)

if __name__ == "__main__":
    print("=" * 60)
    print("DRAFT PICK TRADES TEST")
    print("=" * 60)
    
    # Run tests
    trade_service = test_trade_service()
    test_draft_order_with_trades()
    test_draft_engine_with_trades()
    
    print("\n" + "=" * 60)
    print("All tests completed successfully!")
    print("=" * 60)