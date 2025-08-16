from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from ..models import Player, Team
from ..services.draft_trade_service import DraftTradeService


@dataclass
class DraftPick:
    pick_number: int
    round: int
    pick_in_round: int
    team_id: int
    player: Player


class DraftEngine:
    def __init__(self, num_teams: int, roster_spots: Dict[str, int], 
                 draft_type: str = "snake", reversal_round: int = 0,
                 trade_service: Optional[DraftTradeService] = None):
        self.num_teams = num_teams
        self.roster_spots = roster_spots
        self.draft_type = draft_type
        self.reversal_round = reversal_round
        self.total_rounds = sum(roster_spots.values())
        self.total_picks = self.total_rounds * num_teams
        self.trade_service = trade_service
        
        self.draft_order = self._generate_draft_order()
        self.draft_results: List[DraftPick] = []
        
    def _generate_draft_order(self) -> List[int]:
        order = []
        
        for round_num in range(1, self.total_rounds + 1):
            if self.draft_type == "snake":
                if round_num == 1:
                    round_order = list(range(1, self.num_teams + 1))  # 1→10
                elif round_num == 2:
                    round_order = list(range(self.num_teams, 0, -1))  # 10→1
                elif self.reversal_round > 0 and round_num == self.reversal_round:
                    # 3rd round reversal: use same order as round 2 (reverse)
                    round_order = list(range(self.num_teams, 0, -1))  # 10→1
                else:
                    # After round 3, normal snake draft resumes
                    # Round 4 should go forward (1→10) since round 3 went reverse
                    if (round_num - 3) % 2 == 1:  # 4-3=1 (odd), so forward
                        round_order = list(range(1, self.num_teams + 1))
                    else:  # 5-3=2 (even), so reverse
                        round_order = list(range(self.num_teams, 0, -1))
            else:  # linear draft
                round_order = list(range(1, self.num_teams + 1))
            
            order.extend(round_order)
        
        return order
    
    def get_current_pick_info(self) -> Tuple[int, int, int, int]:
        pick_number = len(self.draft_results) + 1
        
        if pick_number > self.total_picks:
            return 0, 0, 0, 0
        
        current_round = ((pick_number - 1) // self.num_teams) + 1
        pick_in_round = ((pick_number - 1) % self.num_teams) + 1
        original_team_on_clock = self.draft_order[pick_number - 1]
        
        # Check if this pick has been traded
        if self.trade_service:
            team_on_clock = self.trade_service.get_pick_owner(original_team_on_clock, current_round)
        else:
            team_on_clock = original_team_on_clock
        
        return pick_number, current_round, pick_in_round, team_on_clock
    
    def make_pick(self, team: Team, player: Player) -> DraftPick:
        pick_number, current_round, pick_in_round, _ = self.get_current_pick_info()
        
        if not team.can_draft_player(player):
            raise ValueError(f"Team {team.name} cannot draft {player.name}")
        
        team.add_player(player)
        
        pick = DraftPick(
            pick_number=pick_number,
            round=current_round,
            pick_in_round=pick_in_round,
            team_id=team.id,
            player=player
        )
        
        self.draft_results.append(pick)
        return pick
    
    def is_draft_complete(self) -> bool:
        return len(self.draft_results) >= self.total_picks
    
    def get_draft_results(self) -> List[DraftPick]:
        return self.draft_results
    
    def get_recent_picks(self, n: int = 20) -> List[DraftPick]:
        return self.draft_results[-n:] if self.draft_results else []