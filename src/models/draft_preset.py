from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class PlayerExclusion:
    team_name: str
    player_name: str
    enabled: bool = True


@dataclass
class DraftPreset:
    enabled: bool = False
    draft_order: List[str] = field(default_factory=list)
    user_position: int = 0  # 0-based index
    player_exclusions: List[PlayerExclusion] = field(default_factory=list)
    
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