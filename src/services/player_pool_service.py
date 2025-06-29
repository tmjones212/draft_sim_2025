from typing import List, Optional, Set
from ..models import Player


class PlayerPoolService:
    """Service for managing the pool of available players"""
    
    def __init__(self, all_players: List[Player]):
        self.all_players = list(all_players)
        self.available_players = list(all_players)
        self.drafted_players: Set[Player] = set()
    
    def get_available_players(self, limit: Optional[int] = None) -> List[Player]:
        """Get list of available players, optionally limited"""
        if limit:
            return self.available_players[:limit]
        return list(self.available_players)
    
    def draft_player(self, player: Player) -> bool:
        """
        Mark a player as drafted.
        Returns True if successful, False if player was already drafted.
        """
        if player not in self.available_players:
            return False
        
        self.available_players.remove(player)
        self.drafted_players.add(player)
        return True
    
    def draft_multiple_players(self, players: List[Player]) -> List[Player]:
        """
        Draft multiple players at once.
        Returns list of successfully drafted players.
        """
        drafted = []
        for player in players:
            if self.draft_player(player):
                drafted.append(player)
        return drafted
    
    def is_player_available(self, player: Player) -> bool:
        """Check if a player is still available"""
        return player in self.available_players
    
    def find_player_by_name(self, name: str) -> Optional[Player]:
        """Find a player by name in available players"""
        for player in self.available_players:
            if player.name.lower() == name.lower():
                return player
        return None
    
    def get_players_by_position(self, position: str) -> List[Player]:
        """Get all available players at a specific position"""
        return [p for p in self.available_players if p.position == position]
    
    def reset(self):
        """Reset the player pool to initial state"""
        self.available_players = list(self.all_players)
        self.drafted_players.clear()
    
    def get_player_index(self, player: Player) -> Optional[int]:
        """Get the index of a player in the available list"""
        try:
            return self.available_players.index(player)
        except ValueError:
            return None