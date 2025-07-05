from dataclasses import dataclass
from typing import Optional


@dataclass
class Player:
    name: str
    position: str
    rank: int
    adp: float
    team: Optional[str] = None
    bye_week: Optional[int] = None
    player_id: Optional[str] = None
    games_2024: Optional[int] = None
    points_2024: Optional[float] = None
    points_2025_proj: Optional[float] = None
    position_rank_2024: Optional[int] = None
    position_rank_proj: Optional[int] = None
    var: Optional[float] = None  # Value Above Replacement
    weekly_stats_2024: Optional[list] = None  # Weekly stats from 2024 season
    
    def __str__(self):
        return f"{self.rank}. {self.name} ({self.position})"
    
    def __repr__(self):
        return f"Player(name='{self.name}', position='{self.position}', rank={self.rank})"
    
    def __hash__(self):
        # Use player_id if available, otherwise use name and position
        if self.player_id:
            return hash(self.player_id)
        return hash((self.name, self.position))
    
    def __eq__(self, other):
        if not isinstance(other, Player):
            return False
        # Compare by player_id if available, otherwise by name and position
        if self.player_id and other.player_id:
            return self.player_id == other.player_id
        return self.name == other.name and self.position == other.position
    
    @property
    def formatted_name(self):
        """Get the formatted version of the player's name"""
        # Import here to avoid circular import
        from ..utils.player_extensions import format_name
        return format_name(self.name)
    
    def format_name(self):
        """Get the formatted version of the player's name (method version)"""
        # Import here to avoid circular import
        from ..utils.player_extensions import format_name
        return format_name(self.name)