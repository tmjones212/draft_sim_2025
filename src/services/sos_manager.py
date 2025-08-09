import csv
import os
from typing import Dict, Optional


class SOSManager:
    """Manager for Strength of Schedule data"""
    
    def __init__(self):
        self.sos_data: Dict[str, Dict[str, int]] = {}
        self.load_sos_data()
    
    def load_sos_data(self) -> None:
        """Load SOS data from CSV file"""
        csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                'strength_of_schedule.csv')
        
        if not os.path.exists(csv_path):
            print(f"Warning: SOS file not found at {csv_path}")
            return
            
        try:
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    team = row['Team']
                    self.sos_data[team] = {
                        'QB': int(row['QB']),
                        'RB': int(row['RB']),
                        'WR': int(row['WR']),
                        'TE': int(row['TE'])
                    }
            print(f"SOS Manager: Loaded {len(self.sos_data)} teams")
        except Exception as e:
            print(f"Error loading SOS data: {e}")
    
    def get_sos(self, team: str, position: str) -> Optional[int]:
        """Get SOS ranking for a team and position
        
        Args:
            team: Team abbreviation (e.g., 'KC', 'BUF')
            position: Position (QB, RB, WR, TE)
            
        Returns:
            SOS ranking (1-32, lower is easier) or None if not found
        """
        if not team or not position:
            return None
            
        # Handle defensive positions (no SOS data)
        if position in ['LB', 'DB', 'DST', 'K']:
            return None
            
        # Map team abbreviations from player data to CSV format
        team_mapping = {
            'ARZ': 'ARI',  # Arizona
            'LA': 'LAR',   # Los Angeles Rams
        }
        mapped_team = team_mapping.get(team, team)
        
        # Get the base position for FLEX players
        if position in ['RB', 'WR', 'TE']:
            sos_position = position
        elif position == 'QB':
            sos_position = 'QB'
        else:
            return None
        
        # Debug: Print first call to see what's happening
        if not hasattr(self, '_debug_printed'):
            print(f"Debug SOS: team={team}, mapped={mapped_team}, pos={position}, sos_pos={sos_position}")
            print(f"  Available teams: {list(self.sos_data.keys())[:5]}")
            print(f"  Result: {self.sos_data.get(mapped_team, {}).get(sos_position)}")
            self._debug_printed = True
            
        return self.sos_data.get(mapped_team, {}).get(sos_position)
    
    def get_sos_display(self, team: str, position: str) -> str:
        """Get formatted SOS display string
        
        Returns a string like "SOS: 5" or empty string if no data
        """
        sos = self.get_sos(team, position)
        if sos is not None:
            return f"{sos}"
        return ""
    
    def get_sos_color(self, sos: Optional[int]) -> str:
        """Get color based on SOS ranking
        
        1-10: Green (easy)
        11-20: Yellow (moderate)
        21-32: Red (hard)
        """
        if sos is None:
            return "#888888"  # Gray for no data
        elif sos <= 10:
            return "#4CAF50"  # Green
        elif sos <= 20:
            return "#FFC107"  # Yellow
        else:
            return "#F44336"  # Red