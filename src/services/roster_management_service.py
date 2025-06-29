from typing import Dict, List, Tuple
from ..models import Team, Player


class RosterManagementService:
    """Service for managing team rosters and roster analysis"""
    
    def __init__(self, roster_spots: Dict[str, int]):
        self.roster_spots = roster_spots
    
    def get_roster_summary(self, team: Team) -> Dict[str, Tuple[int, int]]:
        """
        Get roster summary showing filled/total spots by position.
        
        Returns:
            Dict mapping position to (filled, total) tuple
        """
        summary = {}
        
        for position, total_spots in self.roster_spots.items():
            filled = len(team.roster.get(position, []))
            summary[position] = (filled, total_spots)
        
        return summary
    
    def get_position_counts(self, team: Team) -> Dict[str, int]:
        """Get count of players by actual position (not roster slot)"""
        position_counts = {'QB': 0, 'RB': 0, 'WR': 0, 'TE': 0, 'DEF': 0, 'K': 0}
        
        for pos_slot, players in team.roster.items():
            for player in players:
                if player.position in position_counts:
                    position_counts[player.position] += 1
        
        return position_counts
    
    def get_team_needs(self, team: Team) -> List[str]:
        """
        Determine team's positional needs based on roster construction.
        Returns positions in priority order.
        """
        needs = []
        position_counts = self.get_position_counts(team)
        
        # Get counts
        qb_count = position_counts['QB']
        rb_count = position_counts['RB']
        wr_count = position_counts['WR']
        te_count = position_counts['TE']
        def_count = position_counts['DEF']
        k_count = position_counts['K']
        
        # Determine needs in priority order
        # Starting positions first
        if qb_count < 1:
            needs.append('QB')
        if rb_count < 2:
            needs.extend(['RB'] * (2 - rb_count))
        if wr_count < 2:
            needs.extend(['WR'] * (2 - wr_count))
        if te_count < 1:
            needs.append('TE')
        
        # FLEX considerations (prefer RB/WR)
        flex_filled = max(0, rb_count - 2) + max(0, wr_count - 2) + max(0, te_count - 1)
        if flex_filled < self.roster_spots.get('FLEX', 0):
            needs.extend(['RB', 'WR'])  # Prefer RB/WR for flex
        
        # Bench depth
        if rb_count < 4:
            needs.append('RB')
        if wr_count < 4:
            needs.append('WR')
        if qb_count < 2:
            needs.append('QB')
        
        # Late round needs
        if def_count < 1:
            needs.append('DEF')
        if k_count < 1:
            needs.append('K')
        
        return needs
    
    def get_roster_by_position(self, team: Team) -> Dict[str, List[Player]]:
        """Get all players grouped by their actual position"""
        roster_by_position = {
            'QB': [], 'RB': [], 'WR': [], 'TE': [], 'DEF': [], 'K': []
        }
        
        for _, players in team.roster.items():
            for player in players:
                if player.position in roster_by_position:
                    roster_by_position[player.position].append(player)
        
        return roster_by_position
    
    def is_position_maxed(self, team: Team, position: str) -> bool:
        """Check if a team has reached max players for a position"""
        position_counts = self.get_position_counts(team)
        
        max_limits = {
            'QB': 2,
            'RB': 5,
            'WR': 5,
            'TE': 2,
            'DEF': 1,
            'K': 1
        }
        
        return position_counts.get(position, 0) >= max_limits.get(position, 99)