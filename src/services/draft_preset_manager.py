import json
import os
from typing import Dict, Optional
from src.models.draft_preset import DraftPreset, PlayerExclusion, ForcedPick, RoundRestriction


class DraftPresetManager:
    def __init__(self, preset_file: str = "data/draft_presets.json"):
        self.preset_file = preset_file
        self.presets: Dict[str, DraftPreset] = {}
        self.active_preset_name: Optional[str] = None
        self.load_presets()
    
    def load_presets(self):
        """Load presets from file"""
        if os.path.exists(self.preset_file):
            try:
                with open(self.preset_file, 'r') as f:
                    data = json.load(f)
                    
                for name, preset_data in data.get('presets', {}).items():
                    preset = DraftPreset(
                        enabled=preset_data.get('enabled', False),
                        draft_order=preset_data.get('draft_order', []),
                        user_position=preset_data.get('user_position', 0),
                        player_exclusions=[
                            PlayerExclusion(
                                team_name=exc['team_name'],
                                player_name=exc['player_name'],
                                enabled=exc.get('enabled', True)
                            )
                            for exc in preset_data.get('player_exclusions', [])
                        ],
                        forced_picks=[
                            ForcedPick(
                                team_name=fp['team_name'],
                                player_name=fp['player_name'],
                                pick_number=fp['pick_number'],
                                enabled=fp.get('enabled', True)
                            )
                            for fp in preset_data.get('forced_picks', [])
                        ],
                        round_restrictions=[
                            RoundRestriction(
                                team_name=rr['team_name'],
                                player_name=rr['player_name'],
                                max_round=rr['max_round'],
                                enabled=rr.get('enabled', True)
                            )
                            for rr in preset_data.get('round_restrictions', [])
                        ]
                    )
                    self.presets[name] = preset
                
                self.active_preset_name = data.get('active_preset')
            except Exception as e:
                print(f"Error loading presets: {e}")
    
    def save_presets(self):
        """Save presets to file"""
        os.makedirs(os.path.dirname(self.preset_file), exist_ok=True)
        
        data = {
            'active_preset': self.active_preset_name,
            'presets': {}
        }
        
        for name, preset in self.presets.items():
            data['presets'][name] = {
                'enabled': preset.enabled,
                'draft_order': preset.draft_order,
                'user_position': preset.user_position,
                'player_exclusions': [
                    {
                        'team_name': exc.team_name,
                        'player_name': exc.player_name,
                        'enabled': exc.enabled
                    }
                    for exc in preset.player_exclusions
                ],
                'forced_picks': [
                    {
                        'team_name': fp.team_name,
                        'player_name': fp.player_name,
                        'pick_number': fp.pick_number,
                        'enabled': fp.enabled
                    }
                    for fp in preset.forced_picks
                ],
                'round_restrictions': [
                    {
                        'team_name': rr.team_name,
                        'player_name': rr.player_name,
                        'max_round': rr.max_round,
                        'enabled': rr.enabled
                    }
                    for rr in preset.round_restrictions
                ]
            }
        
        with open(self.preset_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def create_preset(self, name: str, preset: DraftPreset):
        """Create or update a preset"""
        self.presets[name] = preset
        self.save_presets()
    
    def delete_preset(self, name: str):
        """Delete a preset"""
        if name in self.presets:
            if self.active_preset_name == name:
                self.active_preset_name = None
            del self.presets[name]
            self.save_presets()
    
    def set_active_preset(self, name: Optional[str]):
        """Set the active preset"""
        if name is None or name in self.presets:
            self.active_preset_name = name
            self.save_presets()
    
    def get_active_preset(self) -> Optional[DraftPreset]:
        """Get the currently active preset"""
        if self.active_preset_name and self.active_preset_name in self.presets:
            return self.presets[self.active_preset_name]
        return None
    
    def get_preset(self, name: str) -> Optional[DraftPreset]:
        """Get a specific preset by name"""
        return self.presets.get(name)
    
    def list_preset_names(self) -> list:
        """Get a list of all preset names"""
        return list(self.presets.keys())
    
    def create_default_preset(self):
        """Create the default preset based on user requirements"""
        draft_order = [
            "Karwan", "Joey", "Peter", "Johnson", "Jerwan", 
            "Stan", "Pat", "Me", "Eric", "Luan"
        ]
        
        preset = DraftPreset(
            enabled=True,
            draft_order=draft_order,
            user_position=7,  # "Me" is at index 7 (8th pick)
            player_exclusions=[
                PlayerExclusion(
                    team_name="Johnson",
                    player_name="JOSH ALLEN",
                    enabled=True
                ),
                PlayerExclusion(
                    team_name="Johnson",
                    player_name="BROCK BOWERS",
                    enabled=True
                ),
                PlayerExclusion(
                    team_name="Luan",
                    player_name="BROCK BOWERS",
                    enabled=True
                )
            ],
            forced_picks=[
                ForcedPick(
                    team_name="Luan",
                    player_name="NICO COLLINS",
                    pick_number=10,
                    enabled=True
                )
            ]
        )
        
        self.create_preset("Default League", preset)
        self.set_active_preset("Default League")