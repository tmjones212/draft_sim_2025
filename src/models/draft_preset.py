from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class PlayerExclusion:
    team_name: str
    player_name: str
    enabled: bool = True


@dataclass
class ForcedPick:
    team_name: str
    player_name: str
    pick_number: int  # Overall pick number (1-based)
    enabled: bool = True


@dataclass
class DraftPreset:
    enabled: bool = False
    draft_order: List[str] = field(default_factory=list)
    user_position: int = 0  # 0-based index
    player_exclusions: List[PlayerExclusion] = field(default_factory=list)
    forced_picks: List[ForcedPick] = field(default_factory=list)
    
    def get_team_name(self, position: int) -> str:
        if self.enabled and 0 <= position < len(self.draft_order):
            return self.draft_order[position]
        return f"Team {position + 1}"
    
    def is_player_excluded(self, team_name: str, player_name: str) -> bool:
        if not self.enabled:
            return False
        
        for exclusion in self.player_exclusions:
            if exclusion.enabled and exclusion.team_name == team_name and exclusion.player_name.upper() == player_name.upper():
                return True
        return False
    
    def get_user_team_name(self) -> Optional[str]:
        if self.enabled and 0 <= self.user_position < len(self.draft_order):
            return self.draft_order[self.user_position]
        return None
    
    def get_forced_pick(self, team_name: str, pick_number: int) -> Optional[str]:
        """Get the forced player name for a team at a specific pick number"""
        if not self.enabled:
            return None
        
        for forced_pick in self.forced_picks:
            if (forced_pick.enabled and 
                forced_pick.team_name == team_name and 
                forced_pick.pick_number == pick_number):
                return forced_pick.player_name
        return None