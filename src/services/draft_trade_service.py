from typing import Dict, List, Tuple, Optional
import json
import os

class DraftTradeService:
    """Service for managing draft pick trades between teams"""
    
    def __init__(self):
        self.trades: List[Dict] = []  # List of trade configurations
        self.traded_picks: Dict[Tuple[int, int], int] = {}  # (team_id, round) -> new_team_id
        
    def add_trade(self, team1_id: int, team1_rounds: List[int], 
                  team2_id: int, team2_rounds: List[int]):
        """
        Add a trade between two teams.
        
        Args:
            team1_id: First team's ID
            team1_rounds: List of round numbers team1 is trading away
            team2_id: Second team's ID  
            team2_rounds: List of round numbers team2 is trading away
        """
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
    
    def clear_trades(self):
        """Clear all trades"""
        self.trades.clear()
        self.traded_picks.clear()
    
    def get_pick_owner(self, original_team_id: int, round_num: int) -> int:
        """
        Get the actual owner of a pick after trades.
        
        Args:
            original_team_id: The team that originally owned the pick
            round_num: The round number
            
        Returns:
            The team ID that currently owns this pick
        """
        return self.traded_picks.get((original_team_id, round_num), original_team_id)
    
    def get_trades_summary(self) -> List[str]:
        """Get a human-readable summary of all trades"""
        summaries = []
        for trade in self.trades:
            team1_picks = ', '.join(f"R{r}" for r in trade['team1_rounds'])
            team2_picks = ', '.join(f"R{r}" for r in trade['team2_rounds'])
            summaries.append(
                f"Team {trade['team1_id']} trades {team1_picks} to "
                f"Team {trade['team2_id']} for {team2_picks}"
            )
        return summaries
    
    def save_trades(self, filepath: str):
        """Save trades to a JSON file"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(self.trades, f, indent=2)
    
    def load_trades(self, filepath: str):
        """Load trades from a JSON file"""
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                trades = json.load(f)
                self.clear_trades()
                for trade in trades:
                    self.add_trade(
                        trade['team1_id'], trade['team1_rounds'],
                        trade['team2_id'], trade['team2_rounds']
                    )