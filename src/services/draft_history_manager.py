"""Draft history manager for saving and loading ongoing drafts"""
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from ..core import DraftPick
from ..models import Player


class DraftHistoryManager:
    """Manages saving and loading draft history for ongoing drafts"""
    
    def __init__(self, history_dir: str = "data/draft_history"):
        self.history_dir = history_dir
        self._ensure_history_directory()
        self.current_draft_id = None
        self.current_draft_name = None
    
    def _ensure_history_directory(self):
        """Ensure the history directory exists"""
        if not os.path.exists(self.history_dir):
            os.makedirs(self.history_dir)
    
    def start_new_draft(self, draft_name: str = None) -> str:
        """Start a new draft session
        
        Returns the draft ID
        """
        # Generate unique draft ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_draft_id = f"draft_{timestamp}"
        
        # Use provided name or generate a default
        if draft_name:
            self.current_draft_name = draft_name
        else:
            self.current_draft_name = f"Draft {datetime.now().strftime('%m/%d/%Y %I:%M %p')}"
        
        # Create initial draft file
        draft_data = {
            "id": self.current_draft_id,
            "name": self.current_draft_name,
            "created": datetime.now().isoformat(),
            "modified": datetime.now().isoformat(),
            "picks": [],
            "user_team_id": None,
            "manual_mode": False,
            "teams": {},
            "config": {
                "num_teams": 10,
                "roster_spots": 17,
                "draft_type": "snake",
                "reversal_round": 3
            }
        }
        
        self._save_draft_data(self.current_draft_id, draft_data)
        return self.current_draft_id
    
    def update_draft_name(self, draft_name: str):
        """Update the name of the current draft"""
        if not self.current_draft_id:
            return
        
        self.current_draft_name = draft_name
        draft_data = self._load_draft_data(self.current_draft_id)
        if draft_data:
            draft_data["name"] = draft_name
            draft_data["modified"] = datetime.now().isoformat()
            self._save_draft_data(self.current_draft_id, draft_data)
    
    def save_pick(self, pick: DraftPick, user_team_id: int = None, manual_mode: bool = False):
        """Save a draft pick to the current draft history"""
        if not self.current_draft_id:
            self.start_new_draft()
        
        draft_data = self._load_draft_data(self.current_draft_id)
        if not draft_data:
            return
        
        # Serialize the pick
        pick_data = {
            "pick_number": pick.pick_number,
            "round": pick.round,
            "pick_in_round": pick.pick_in_round,
            "team_id": pick.team_id,
            "player": {
                "name": pick.player.name,
                "position": pick.player.position,
                "team": pick.player.team,
                "adp": pick.player.adp,
                "player_id": pick.player.player_id,
                "var_rank": getattr(pick.player, 'var_rank', None),
                "pos_rank": getattr(pick.player, 'pos_rank', None)
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # Update picks list (overwrite if pick already exists)
        picks = draft_data.get("picks", [])
        # Remove any existing pick with same pick_number
        picks = [p for p in picks if p["pick_number"] != pick.pick_number]
        picks.append(pick_data)
        picks.sort(key=lambda x: x["pick_number"])
        
        draft_data["picks"] = picks
        draft_data["user_team_id"] = user_team_id
        draft_data["manual_mode"] = manual_mode
        draft_data["modified"] = datetime.now().isoformat()
        
        self._save_draft_data(self.current_draft_id, draft_data)
    
    def remove_picks_after(self, pick_number: int):
        """Remove all picks after a certain pick number (for reversion)"""
        if not self.current_draft_id:
            return
        
        draft_data = self._load_draft_data(self.current_draft_id)
        if not draft_data:
            return
        
        # Filter out picks after the specified number
        picks = draft_data.get("picks", [])
        picks = [p for p in picks if p["pick_number"] <= pick_number]
        
        draft_data["picks"] = picks
        draft_data["modified"] = datetime.now().isoformat()
        
        self._save_draft_data(self.current_draft_id, draft_data)
    
    def save_team_config(self, teams: Dict, user_team_id: int = None, manual_mode: bool = False):
        """Save team configuration"""
        if not self.current_draft_id:
            self.start_new_draft()
        
        draft_data = self._load_draft_data(self.current_draft_id)
        if not draft_data:
            return
        
        # Serialize teams
        teams_data = {}
        for team_id, team in teams.items():
            teams_data[str(team_id)] = {
                "name": team.name,
                "draft_position": getattr(team, 'draft_position', team_id)
            }
        
        draft_data["teams"] = teams_data
        draft_data["user_team_id"] = user_team_id
        draft_data["manual_mode"] = manual_mode
        draft_data["modified"] = datetime.now().isoformat()
        
        self._save_draft_data(self.current_draft_id, draft_data)
    
    def get_draft_list(self) -> List[Dict[str, Any]]:
        """Get list of all saved drafts"""
        drafts = []
        
        if os.path.exists(self.history_dir):
            for filename in sorted(os.listdir(self.history_dir), reverse=True):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.history_dir, filename)
                    try:
                        with open(filepath, 'r') as f:
                            data = json.load(f)
                            user_team_id = data.get("user_team_id")
                            user_team_name = "No Team"
                            if user_team_id is not None and "teams" in data:
                                team_info = data["teams"].get(str(user_team_id), {})
                                user_team_name = team_info.get("name", f"Team {user_team_id}")
                            
                            drafts.append({
                                "id": data.get("id"),
                                "name": data.get("name", "Untitled Draft"),
                                "created": data.get("created"),
                                "modified": data.get("modified"),
                                "picks_count": len(data.get("picks", [])),
                                "user_team": user_team_name,
                                "user_team_id": user_team_id,
                                "manual_mode": data.get("manual_mode", False),
                                "total_picks": len(data.get("picks", []))
                            })
                    except:
                        continue
        
        return drafts
    
    def load_draft(self, draft_id: str) -> Dict[str, Any]:
        """Load a saved draft"""
        draft_data = self._load_draft_data(draft_id)
        if draft_data:
            self.current_draft_id = draft_id
            self.current_draft_name = draft_data.get("name", "Untitled Draft")
        return draft_data
    
    def delete_draft(self, draft_id: str):
        """Delete a saved draft"""
        filepath = os.path.join(self.history_dir, f"{draft_id}.json")
        if os.path.exists(filepath):
            os.remove(filepath)
            if self.current_draft_id == draft_id:
                self.current_draft_id = None
                self.current_draft_name = None
    
    def _save_draft_data(self, draft_id: str, data: Dict[str, Any]):
        """Save draft data to file"""
        filepath = os.path.join(self.history_dir, f"{draft_id}.json")
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _load_draft_data(self, draft_id: str) -> Optional[Dict[str, Any]]:
        """Load draft data from file"""
        filepath = os.path.join(self.history_dir, f"{draft_id}.json")
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
        return None