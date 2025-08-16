from typing import List, Tuple, Optional
from .draft_trade_service import DraftTradeService


class DraftOrderService:
    """Service for managing draft order calculations and pick information"""
    
    def __init__(self, num_teams: int, reversal_round: int = 3, trade_service: Optional[DraftTradeService] = None):
        self.num_teams = num_teams
        self.reversal_round = reversal_round
        self.trade_service = trade_service
    
    def get_draft_order_for_round(self, round_num: int) -> List[int]:
        """
        Get the team draft order for a specific round.
        Handles 3rd round reversal where rounds 2 and 3 go the same direction.
        """
        if round_num == 1:
            return list(range(1, self.num_teams + 1))
        elif round_num == 2 or round_num == 3:
            # Rounds 2 and 3 go the same direction (reverse)
            return list(range(self.num_teams, 0, -1))
        else:
            # After round 3, normal snake draft
            # Round 4 goes forward, round 5 reverse, etc.
            if round_num % 2 == 0:
                return list(range(1, self.num_teams + 1))
            else:
                return list(range(self.num_teams, 0, -1))
    
    def get_pick_info(self, pick_number: int, total_rounds: int) -> Tuple[int, int, int]:
        """
        Get round number, pick in round, and team ID for a given pick number.
        Takes into account any trades that have been configured.
        
        Returns:
            Tuple of (round_number, pick_in_round, team_id)
        """
        # Calculate round (1-indexed)
        round_num = ((pick_number - 1) // self.num_teams) + 1
        
        # Calculate pick within the round (1-indexed)
        pick_in_round = ((pick_number - 1) % self.num_teams) + 1
        
        # Get team order for this round
        order = self.get_draft_order_for_round(round_num)
        
        # Get the original team ID (position in order)
        original_team_id = order[pick_in_round - 1]
        
        # Check if this pick has been traded
        if self.trade_service:
            team_id = self.trade_service.get_pick_owner(original_team_id, round_num)
        else:
            team_id = original_team_id
        
        return round_num, pick_in_round, team_id
    
    def get_pick_label(self, round_num: int, pick_in_round: int) -> str:
        """Get the display label for a pick (e.g., 'R1.5')"""
        return f"R{round_num}.{pick_in_round}"
    
    def calculate_total_picks(self, total_rounds: int) -> int:
        """Calculate total number of picks in the draft"""
        return self.num_teams * total_rounds