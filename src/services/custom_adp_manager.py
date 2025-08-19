import json
import os
import sys
from typing import Dict, Optional


class CustomADPManager:
    """Manages custom ADP values that persist between app sessions"""
    
    def __init__(self):
        # Path to store custom ADP values
        # Use a persistent location that works both in development and when bundled as exe
        if getattr(sys, 'frozen', False):
            # Running as bundled exe - use user's AppData folder
            if sys.platform == 'win32':
                app_data = os.environ.get('APPDATA', os.path.expanduser('~'))
                self.data_dir = os.path.join(app_data, 'MockDraftSim2025')
            else:
                # Mac/Linux
                self.data_dir = os.path.join(os.path.expanduser('~'), '.mock_draft_sim_2025')
            
            # Check for bundled custom_adp.json and copy if needed
            bundled_data_dir = os.path.join(sys._MEIPASS, 'data') if hasattr(sys, '_MEIPASS') else 'data'
            bundled_custom_adp = os.path.join(bundled_data_dir, 'custom_adp.json')
            user_custom_adp = os.path.join(self.data_dir, 'custom_adp.json')
            
            # If user doesn't have custom_adp.json but bundled version exists, copy it
            if not os.path.exists(user_custom_adp) and os.path.exists(bundled_custom_adp):
                os.makedirs(self.data_dir, exist_ok=True)
                import shutil
                shutil.copy2(bundled_custom_adp, user_custom_adp)
                print(f"Copied bundled custom_adp.json to {user_custom_adp}")
        else:
            # Running from source - use project data directory
            self.data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
        
        self.custom_adp_file = os.path.join(self.data_dir, 'custom_adp.json')
        self.custom_adp_values: Dict[str, float] = {}
        self.load_custom_adp()
    
    def load_custom_adp(self) -> None:
        """Load custom ADP values from file"""
        if os.path.exists(self.custom_adp_file):
            try:
                with open(self.custom_adp_file, 'r') as f:
                    self.custom_adp_values = json.load(f)
                print(f"Loaded {len(self.custom_adp_values)} custom ADP values")
            except Exception as e:
                print(f"Error loading custom ADP values: {e}")
                self.custom_adp_values = {}
    
    def save_custom_adp(self) -> None:
        """Save custom ADP values to file"""
        try:
            # Ensure data directory exists
            os.makedirs(self.data_dir, exist_ok=True)
            
            with open(self.custom_adp_file, 'w') as f:
                json.dump(self.custom_adp_values, f, indent=2)
            print(f"Saved {len(self.custom_adp_values)} custom ADP values")
        except Exception as e:
            print(f"Error saving custom ADP values: {e}")
    
    def set_custom_adp(self, player_id: str, adp: float) -> None:
        """Set a custom ADP value for a player"""
        self.custom_adp_values[player_id] = adp
        self.save_custom_adp()
    
    def get_custom_adp(self, player_id: str) -> Optional[float]:
        """Get custom ADP value for a player"""
        return self.custom_adp_values.get(player_id)
    
    def remove_custom_adp(self, player_id: str) -> None:
        """Remove custom ADP value for a player"""
        if player_id in self.custom_adp_values:
            del self.custom_adp_values[player_id]
            self.save_custom_adp()
    
    def clear_all_custom_adp(self) -> None:
        """Clear all custom ADP values"""
        self.custom_adp_values = {}
        self.save_custom_adp()
    
    def apply_custom_adp_to_players(self, players: list) -> None:
        """Apply custom ADP values to a list of players"""
        for player in players:
            if hasattr(player, 'player_id') and player.player_id in self.custom_adp_values:
                player.adp = self.custom_adp_values[player.player_id]