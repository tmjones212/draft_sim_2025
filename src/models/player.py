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
    
    def __str__(self):
        return f"{self.rank}. {self.name} ({self.position})"
    
    def __repr__(self):
        return f"Player(name='{self.name}', position='{self.position}', rank={self.rank})"