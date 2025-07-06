from typing import Dict, List
from .player import Player


class Team:
    def __init__(self, team_id: int, name: str, roster_spots: Dict[str, int]):
        self.id = team_id
        self.name = name
        self.roster_spots = roster_spots
        self.roster = {pos: [] for pos in roster_spots}
        
    def can_draft_player(self, player: Player) -> bool:
        pos = player.position.lower()
        
        # Check starting position slots
        if pos in ["qb", "te"]:
            if len(self.roster[pos]) < self.roster_spots[pos]:
                return True
        elif pos in ["rb", "wr"]:
            if len(self.roster[pos]) < self.roster_spots[pos]:
                return True
        
        # Check flex eligibility
        if player.position in ["RB", "WR", "TE"]:
            flex_filled = sum(1 for p in self.roster["flex"] 
                            if p.position in ["RB", "WR", "TE"])
            if flex_filled < self.roster_spots["flex"]:
                return True
        
        # Check bench
        if len(self.roster["bn"]) < self.roster_spots["bn"]:
            return True
        
        return False
    
    def add_player(self, player: Player) -> bool:
        pos = player.position.lower()
        
        # Try to fill starting position first
        if pos in ["qb", "te"]:
            if len(self.roster[pos]) < self.roster_spots[pos]:
                self.roster[pos].append(player)
                return True
        elif pos in ["rb", "wr"]:
            if len(self.roster[pos]) < self.roster_spots[pos]:
                self.roster[pos].append(player)
                return True
        
        # Try flex
        if player.position in ["RB", "WR", "TE"]:
            flex_filled = sum(1 for p in self.roster["flex"] 
                            if p.position in ["RB", "WR", "TE"])
            if flex_filled < self.roster_spots["flex"]:
                self.roster["flex"].append(player)
                return True
        
        # Add to bench
        if len(self.roster["bn"]) < self.roster_spots["bn"]:
            self.roster["bn"].append(player)
            return True
        
        return False
    
    def get_roster_summary(self) -> Dict[str, List[Player]]:
        return self.roster
    
    def is_roster_full(self) -> bool:
        total_spots = sum(self.roster_spots.values())
        total_filled = sum(len(players) for players in self.roster.values())
        return total_filled >= total_spots