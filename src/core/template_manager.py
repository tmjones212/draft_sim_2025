import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from src.models.player import Player
from src.models.team import Team
from src.core.draft_logic import DraftPick


class DraftTemplate:
    def __init__(self, name: str):
        self.name = name
        self.created_at = datetime.now().isoformat()
        self.draft_config = {}
        self.draft_results = []
        self.team_states = {}
        self.player_pool = {}
        self.user_settings = {}
        self.notes = ""
        self.trades = []  # Store trade configurations
        self.grade = None  # Grade from 1-100
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "created_at": self.created_at,
            "draft_config": self.draft_config,
            "draft_results": self.draft_results,
            "team_states": self.team_states,
            "player_pool": self.player_pool,
            "user_settings": self.user_settings,
            "notes": self.notes,
            "trades": self.trades,
            "grade": self.grade
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DraftTemplate':
        template = cls(data["name"])
        template.created_at = data.get("created_at", datetime.now().isoformat())
        template.draft_config = data.get("draft_config", {})
        template.draft_results = data.get("draft_results", [])
        template.team_states = data.get("team_states", {})
        template.player_pool = data.get("player_pool", {})
        template.user_settings = data.get("user_settings", {})
        template.notes = data.get("notes", "")
        template.trades = data.get("trades", [])
        template.grade = data.get("grade", None)
        return template


class TemplateManager:
    def __init__(self, templates_dir: str = "templates"):
        self.templates_dir = templates_dir
        os.makedirs(templates_dir, exist_ok=True)
    
    def save_template(self, 
                     name: str,
                     draft_engine,
                     teams: List[Team],
                     available_players: List[Player],
                     all_players: List[Player],
                     user_team_id: int,
                     manual_mode: bool,
                     custom_rankings: Optional[Dict[str, int]] = None,
                     player_tiers: Optional[Dict[str, int]] = None,
                     watch_list: Optional[List[str]] = None,
                     trade_service=None) -> bool:
        """Save current draft state as a template"""
        try:
            template = DraftTemplate(name)
            
            # Save draft configuration
            pick_number, current_round, pick_in_round, team_on_clock = draft_engine.get_current_pick_info()
            template.draft_config = {
                "num_teams": draft_engine.num_teams,
                "roster_spots": draft_engine.roster_spots,
                "draft_type": draft_engine.draft_type,
                "reversal_round": draft_engine.reversal_round,
                "current_pick": {
                    "pick_number": pick_number,
                    "round": current_round,
                    "pick_in_round": pick_in_round,
                    "team_on_clock": team_on_clock
                }
            }
            
            # Save draft results
            template.draft_results = []
            for pick in draft_engine.draft_results:
                template.draft_results.append({
                    "pick_number": pick.pick_number,
                    "round": pick.round,
                    "pick_in_round": pick.pick_in_round,
                    "team_id": pick.team_id,
                    "player_id": pick.player.player_id if pick.player else None
                })
            
            # Save team states
            template.team_states = {}
            for team in teams:
                team_data = {
                    "name": team.name,
                    "roster": {}
                }
                for position, players in team.roster.items():
                    team_data["roster"][position] = [p.player_id for p in players]
                template.team_states[str(team.id)] = team_data
            
            # Save player pool
            template.player_pool = {
                "available_player_ids": [p.player_id for p in available_players],
                "all_players": [{
                    "player_id": p.player_id,
                    "name": p.name,
                    "position": p.position,
                    "rank": p.rank,
                    "adp": p.adp,
                    "team": p.team,
                    "bye_week": p.bye_week,
                    "points_2024": p.points_2024,
                    "points_2025_proj": p.points_2025_proj,
                    "var": p.var,
                    "games_2024": p.games_2024,
                    "position_rank_2024": p.position_rank_2024,
                    "position_rank_proj": p.position_rank_proj,
                    "weekly_stats_2024": p.weekly_stats_2024
                } for p in all_players]
            }
            
            # Save user settings
            template.user_settings = {
                "user_team_id": user_team_id,
                "manual_mode": manual_mode,
                "custom_rankings": custom_rankings or {},
                "player_tiers": player_tiers or {},
                "watch_list": watch_list or []
            }
            
            # Save trades if trade service is provided
            if trade_service:
                template.trades = trade_service.trades
            
            # Write to file
            filename = f"{name.replace(' ', '_').lower()}.json"
            filepath = os.path.join(self.templates_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump(template.to_dict(), f, indent=2)
            
            return True
            
        except Exception as e:
            print(f"Error saving template: {e}")
            return False
    
    def load_template(self, filename: str) -> Optional[DraftTemplate]:
        """Load a template from file"""
        try:
            filepath = os.path.join(self.templates_dir, filename)
            with open(filepath, 'r') as f:
                data = json.load(f)
            return DraftTemplate.from_dict(data)
        except Exception as e:
            print(f"Error loading template: {e}")
            return None
    
    def list_templates(self) -> List[Dict[str, str]]:
        """List all available templates"""
        templates = []
        try:
            for filename in os.listdir(self.templates_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.templates_dir, filename)
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                    templates.append({
                        "filename": filename,
                        "name": data.get("name", filename),
                        "created_at": data.get("created_at", "Unknown")
                    })
        except Exception as e:
            print(f"Error listing templates: {e}")
        
        return sorted(templates, key=lambda x: x["created_at"], reverse=True)
    
    def delete_template(self, filename: str) -> bool:
        """Delete a template"""
        try:
            filepath = os.path.join(self.templates_dir, filename)
            os.remove(filepath)
            return True
        except Exception as e:
            print(f"Error deleting template: {e}")
            return False
    
    def update_template_notes(self, filename: str, notes: str) -> bool:
        """Update the notes for a template"""
        try:
            template = self.load_template(filename)
            if not template:
                return False
            
            template.notes = notes
            
            # Write back to file
            filepath = os.path.join(self.templates_dir, filename)
            with open(filepath, 'w') as f:
                json.dump(template.to_dict(), f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error updating template notes: {e}")
            return False
    
    def update_template_grade(self, filename: str, grade: Optional[int]) -> bool:
        """Update the grade for a template (1-100 or None)"""
        try:
            template = self.load_template(filename)
            if not template:
                return False
            
            if grade is not None:
                # Validate grade is between 1 and 100
                grade = max(1, min(100, grade))
            
            template.grade = grade
            
            # Write back to file
            filepath = os.path.join(self.templates_dir, filename)
            with open(filepath, 'w') as f:
                json.dump(template.to_dict(), f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error updating template grade: {e}")
            return False