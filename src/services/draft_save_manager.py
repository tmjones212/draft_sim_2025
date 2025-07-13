"""Draft save manager for saving completed mock drafts"""
import json
import os
from datetime import datetime
from typing import List, Dict, Any
from ..core import DraftPick
from ..models import Team, Player


class DraftSaveManager:
    """Manages saving and loading draft results"""
    
    def __init__(self, save_dir: str = "data/saved_drafts"):
        self.save_dir = save_dir
        self._ensure_save_directory()
    
    def _ensure_save_directory(self):
        """Ensure the save directory exists"""
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
    
    def save_draft(self, draft_results: List[DraftPick], teams: Dict[str, Team], 
                   user_team_id: str = None, manual_mode: bool = False) -> str:
        """Save a completed draft to JSON file
        
        Returns the filename of the saved draft
        """
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"mock_draft_{timestamp}.json"
        filepath = os.path.join(self.save_dir, filename)
        
        # Prepare draft data
        draft_data = {
            "timestamp": datetime.now().isoformat(),
            "user_team_id": user_team_id,
            "manual_mode": manual_mode,
            "total_picks": len(draft_results),
            "teams": self._serialize_teams(teams),
            "picks": self._serialize_picks(draft_results),
            "summary": self._generate_summary(draft_results, teams, user_team_id)
        }
        
        # Save to file
        with open(filepath, 'w') as f:
            json.dump(draft_data, f, indent=2)
        
        return filename
    
    def _serialize_teams(self, teams: Dict[str, Team]) -> List[Dict[str, Any]]:
        """Serialize team data"""
        serialized_teams = []
        for team_id, team in teams.items():
            team_data = {
                "id": team_id,
                "name": team.name,
                "draft_position": team.draft_position,
                "roster": {}
            }
            
            # Serialize roster
            for position, players in team.roster.items():
                team_data["roster"][position] = [
                    {
                        "name": player.name,
                        "position": player.position,
                        "team": player.team,
                        "adp": player.adp,
                        "player_id": player.player_id
                    }
                    for player in players
                ]
            
            serialized_teams.append(team_data)
        
        return serialized_teams
    
    def _serialize_picks(self, draft_results: List[DraftPick]) -> List[Dict[str, Any]]:
        """Serialize draft picks"""
        serialized_picks = []
        for pick in draft_results:
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
                    "adp_diff": pick.player.adp - pick.pick_number if pick.player.adp else None
                }
            }
            serialized_picks.append(pick_data)
        
        return serialized_picks
    
    def _generate_summary(self, draft_results: List[DraftPick], teams: Dict[str, Team], 
                         user_team_id: str = None) -> Dict[str, Any]:
        """Generate draft summary statistics"""
        summary = {
            "total_rounds": max(pick.round for pick in draft_results) if draft_results else 0,
            "value_picks": [],  # Picks that fell below ADP
            "reach_picks": [],  # Picks above ADP
            "position_distribution": {}
        }
        
        # Analyze each pick
        for pick in draft_results:
            # Value/reach analysis
            if pick.player.adp:
                diff = pick.player.adp - pick.pick_number
                if diff >= 5:  # Fell 5+ spots
                    summary["value_picks"].append({
                        "pick": pick.pick_number,
                        "player": pick.player.name,
                        "adp": pick.player.adp,
                        "value": int(diff)
                    })
                elif diff <= -5:  # Reached 5+ spots
                    summary["reach_picks"].append({
                        "pick": pick.pick_number,
                        "player": pick.player.name,
                        "adp": pick.player.adp,
                        "reach": int(abs(diff))
                    })
            
            # Position distribution
            pos = pick.player.position
            if pos not in summary["position_distribution"]:
                summary["position_distribution"][pos] = 0
            summary["position_distribution"][pos] += 1
        
        # Sort value/reach picks
        summary["value_picks"].sort(key=lambda x: x["value"], reverse=True)
        summary["reach_picks"].sort(key=lambda x: x["reach"], reverse=True)
        
        # User team summary if applicable
        if user_team_id and user_team_id in teams:
            user_team = teams[user_team_id]
            user_picks = [p for p in draft_results if p.team_id == user_team_id]
            
            summary["user_team"] = {
                "name": user_team.name,
                "picks": len(user_picks),
                "positions_drafted": {}
            }
            
            for pick in user_picks:
                pos = pick.player.position
                if pos not in summary["user_team"]["positions_drafted"]:
                    summary["user_team"]["positions_drafted"][pos] = 0
                summary["user_team"]["positions_drafted"][pos] += 1
        
        return summary
    
    def get_saved_drafts(self) -> List[Dict[str, Any]]:
        """Get list of saved drafts with basic info"""
        saved_drafts = []
        
        if os.path.exists(self.save_dir):
            for filename in sorted(os.listdir(self.save_dir), reverse=True):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.save_dir, filename)
                    try:
                        with open(filepath, 'r') as f:
                            data = json.load(f)
                            saved_drafts.append({
                                "filename": filename,
                                "timestamp": data.get("timestamp"),
                                "user_team": data.get("teams", [{}])[0].get("name") if data.get("user_team_id") else "Observer",
                                "total_picks": data.get("total_picks", 0),
                                "manual_mode": data.get("manual_mode", False)
                            })
                    except:
                        continue
        
        return saved_drafts
    
    def load_draft(self, filename: str) -> Dict[str, Any]:
        """Load a saved draft"""
        filepath = os.path.join(self.save_dir, filename)
        with open(filepath, 'r') as f:
            return json.load(f)