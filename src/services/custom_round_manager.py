import json
import os
from typing import Dict, Optional


class CustomRoundManager:
    """Manages custom round assignments for draft planning"""
    
    def __init__(self):
        # Path to store custom round values
        self.data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
        self.custom_round_file = os.path.join(self.data_dir, 'custom_rounds.json')
        self.custom_round_values: Dict[str, int] = {}
        self.load_custom_rounds()
    
    def load_custom_rounds(self) -> None:
        """Load custom round values from file"""
        if os.path.exists(self.custom_round_file):
            try:
                with open(self.custom_round_file, 'r') as f:
                    self.custom_round_values = json.load(f)
                print(f"Loaded {len(self.custom_round_values)} custom round values")
            except Exception as e:
                print(f"Error loading custom round values: {e}")
                self.custom_round_values = {}
    
    def save_custom_rounds(self) -> None:
        """Save custom round values to file"""
        try:
            # Ensure data directory exists
            os.makedirs(self.data_dir, exist_ok=True)
            
            with open(self.custom_round_file, 'w') as f:
                json.dump(self.custom_round_values, f, indent=2)
            print(f"Saved {len(self.custom_round_values)} custom round values")
        except Exception as e:
            print(f"Error saving custom round values: {e}")
    
    def set_custom_round(self, player_id: str, round_num: int) -> None:
        """Set a custom round value for a player"""
        if round_num == 0:  # 0 means remove custom round
            self.remove_custom_round(player_id)
        else:
            self.custom_round_values[player_id] = round_num
            self.save_custom_rounds()
    
    def get_custom_round(self, player_id: str) -> Optional[int]:
        """Get custom round value for a player"""
        return self.custom_round_values.get(player_id)
    
    def remove_custom_round(self, player_id: str) -> None:
        """Remove custom round value for a player"""
        if player_id in self.custom_round_values:
            del self.custom_round_values[player_id]
            self.save_custom_rounds()
    
    def clear_all_custom_rounds(self) -> None:
        """Clear all custom round values"""
        self.custom_round_values = {}
        self.save_custom_rounds()
    
    def get_players_by_round(self, round_num: int) -> list:
        """Get all player IDs assigned to a specific round"""
        return [pid for pid, rnd in self.custom_round_values.items() if rnd == round_num]