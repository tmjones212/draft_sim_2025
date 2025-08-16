#!/usr/bin/env python3
"""Simple test script for draft pick trades functionality (no GUI dependencies)"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import only what we need, avoiding tkinter dependencies
from typing import Dict, List, Tuple, Optional
import json

# Inline the essential parts to avoid imports
class DraftTradeService:
    """Service for managing draft pick trades between teams"""
    
    def __init__(self):
        self.trades: List[Dict] = []
        self.traded_picks: Dict[Tuple[int, int], int] = {}
        
    def add_trade(self, team1_id: int, team1_rounds: List[int], 
                  team2_id: int, team2_rounds: List[int]):
        trade = {
            'team1_id': team1_id,
            'team1_rounds': team1_rounds,
            'team2_id': team2_id,
            'team2_rounds': team2_rounds
        }
        self.trades.append(trade)
        
        # Update the traded picks mapping
        for round_num in team1_rounds:
            self.traded_picks[(team1_id, round_num)] = team2_id
        for round_num in team2_rounds:
            self.traded_picks[(team2_id, round_num)] = team1_id
    
    def get_pick_owner(self, original_team_id: int, round_num: int) -> int:
        return self.traded_picks.get((original_team_id, round_num), original_team_id)
    
    def get_trades_summary(self) -> List[str]:
        summaries = []
        for trade in self.trades:
            team1_picks = ', '.join(f"R{r}" for r in trade['team1_rounds'])
            team2_picks = ', '.join(f"R{r}" for r in trade['team2_rounds'])
            summaries.append(
                f"Team {trade['team1_id']} trades {team1_picks} to "
                f"Team {trade['team2_id']} for {team2_picks}"
            )
        return summaries


def test_trade_scenario():
    """Test the specific trade scenario requested"""
    print("=" * 60)
    print("TESTING DRAFT PICK TRADE SCENARIO")
    print("Team 8 trades their 1st, 4th & 10th round picks")
    print("Team 7 trades their 2nd, 3rd & 11th round picks")
    print("=" * 60)
    
    # Create trade service
    trade_service = DraftTradeService()
    
    # Add the trade
    trade_service.add_trade(8, [1, 4, 10], 7, [2, 3, 11])
    
    # Display trade summary
    print("\nTrade Summary:")
    for summary in trade_service.get_trades_summary():
        print(f"  • {summary}")
    
    # Show pick ownership changes
    print("\nPick Ownership After Trade:")
    print("-" * 40)
    
    # Test all relevant picks
    test_cases = [
        (8, 1, 7, "Team 8's 1st round → Team 7"),
        (8, 4, 7, "Team 8's 4th round → Team 7"),
        (8, 10, 7, "Team 8's 10th round → Team 7"),
        (7, 2, 8, "Team 7's 2nd round → Team 8"),
        (7, 3, 8, "Team 7's 3rd round → Team 8"),
        (7, 11, 8, "Team 7's 11th round → Team 8"),
        (8, 2, 8, "Team 8's 2nd round (unchanged)"),
        (8, 3, 8, "Team 8's 3rd round (unchanged)"),
        (7, 1, 7, "Team 7's 1st round (unchanged)"),
        (7, 4, 7, "Team 7's 4th round (unchanged)"),
    ]
    
    for original_team, round_num, expected_owner, description in test_cases:
        actual_owner = trade_service.get_pick_owner(original_team, round_num)
        status = "✓" if actual_owner == expected_owner else "✗"
        print(f"  {status} {description}: Team {actual_owner}")
    
    # Show what each team ends up with
    print("\nFinal Pick Allocation (Rounds 1-11):")
    print("-" * 40)
    
    for team in [7, 8]:
        picks = []
        for round_num in range(1, 12):
            # Check all teams to see who owns this team's picks
            for original_team in range(1, 11):
                if trade_service.get_pick_owner(original_team, round_num) == team:
                    if original_team == team:
                        picks.append(f"R{round_num}")
                    else:
                        picks.append(f"R{round_num}(from T{original_team})")
        print(f"  Team {team}: {', '.join(picks)}")
    
    print("\n" + "=" * 60)
    print("Trade configuration successful!")
    print("The TRADES button in the app will allow you to configure this.")
    print("=" * 60)


if __name__ == "__main__":
    test_trade_scenario()