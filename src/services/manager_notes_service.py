import os
import sys
import json
from typing import Dict, Optional

class ManagerNotesService:
    """Service for managing draft habit notes for managers"""
    
    # Manager name mappings (draft page name -> archive name)
    MANAGER_MAPPINGS = {
        "HE HATE ME": "KARWAN",
        "Joey": "JOEY", 
        "P-Nasty": "PETER",
        "Erich": "ERIC",
        "champ": "JERWAN",
        "Stan": "STAN",
        "PatrickS": "PAT",
        "Trent": "ME",
        "johnson": "JOHNSON",
        "luan": "LUAN"
    }
    
    # Reverse mapping for lookups
    REVERSE_MAPPINGS = {v.upper(): k for k, v in MANAGER_MAPPINGS.items()}
    
    def __init__(self):
        # Use a persistent location that works both in development and when bundled as exe
        if getattr(sys, 'frozen', False):
            # Running as bundled exe - use user's AppData folder
            if sys.platform == 'win32':
                app_data = os.environ.get('APPDATA', os.path.expanduser('~'))
                data_dir = os.path.join(app_data, 'MockDraftSim2025')
            else:
                # Mac/Linux
                data_dir = os.path.join(os.path.expanduser('~'), '.mock_draft_sim_2025')
        else:
            # Running from source - use project data directory
            data_dir = "data"
        
        # Ensure directory exists
        os.makedirs(data_dir, exist_ok=True)
        self.notes_file = os.path.join(data_dir, "manager_notes.json")
        self.notes = self._load_notes()
    
    def _load_notes(self) -> Dict[str, str]:
        """Load manager notes from file"""
        if os.path.exists(self.notes_file):
            try:
                with open(self.notes_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_notes(self):
        """Save manager notes to file"""
        os.makedirs("data", exist_ok=True)
        with open(self.notes_file, 'w') as f:
            json.dump(self.notes, f, indent=2)
    
    def get_note(self, manager_name: str) -> str:
        """Get note for a manager (works with both draft and archive names)"""
        # Check if it's a draft page name (case-insensitive)
        for draft_name, archive_name in self.MANAGER_MAPPINGS.items():
            if manager_name.upper() == draft_name.upper():
                return self.notes.get(archive_name, "")
        
        # Check if it's already an archive name
        return self.notes.get(manager_name.upper(), "")
    
    def set_note(self, manager_name: str, note: str):
        """Set note for a manager (archive name format)"""
        # Always store with archive name (uppercase)
        manager_name_upper = manager_name.upper()
        if note.strip():
            self.notes[manager_name_upper] = note.strip()
        elif manager_name_upper in self.notes:
            del self.notes[manager_name_upper]
        self.save_notes()
    
    def get_draft_name(self, archive_name: str) -> str:
        """Convert archive name to draft page name"""
        return self.REVERSE_MAPPINGS.get(archive_name.upper(), archive_name)
    
    def get_archive_name(self, draft_name: str) -> str:
        """Convert draft page name to archive name"""
        return self.MANAGER_MAPPINGS.get(draft_name, draft_name.upper())