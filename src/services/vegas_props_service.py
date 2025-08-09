"""Service for managing DraftKings Vegas props data"""

import threading
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from .draftkings_api import DraftKingsAPI, PlayerProp

@dataclass
class CachedPropsData:
    """Container for cached props data"""
    data: Dict[str, List[PlayerProp]]
    timestamp: datetime
    
class VegasPropsService:
    """Service to manage Vegas props data from DraftKings"""
    
    def __init__(self, on_props_loaded=None):
        self.cache: Optional[CachedPropsData] = None
        self.cache_duration = timedelta(minutes=15)
        self.loading = False
        self.load_lock = threading.Lock()
        self.on_props_loaded = on_props_loaded
        
        # Start background load on initialization
        self._start_background_load()
        
    def get_all_props(self, force_refresh: bool = False) -> Dict[str, List[PlayerProp]]:
        """Get all common props, using cache if available"""
        with self.load_lock:
            # Check if we need to refresh
            if force_refresh or self._should_refresh():
                self._refresh_cache()
            
            if self.cache:
                return self.cache.data
            return {}
    
    def get_player_props(self, player_name: str) -> Dict[str, PlayerProp]:
        """Get all props for a specific player"""
        all_props = self.get_all_props()
        player_props = {}
        
        # Format the player name for matching (use the API's format_name)
        from .draftkings_api import format_name
        formatted_name = format_name(player_name)
        
        # Search through all prop types
        for prop_type, props_list in all_props.items():
            for prop in props_list:
                if format_name(prop.player_name) == formatted_name:
                    player_props[prop_type] = prop
                    break
        
        return player_props
    
    def get_prop_value(self, player_name: str, prop_type: str) -> Optional[float]:
        """Get a specific prop value for a player"""
        player_props = self.get_player_props(player_name)
        if prop_type in player_props:
            return player_props[prop_type].prop_value
        return None
    
    def _should_refresh(self) -> bool:
        """Check if cache should be refreshed"""
        if not self.cache:
            return True
        
        age = datetime.now() - self.cache.timestamp
        return age > self.cache_duration
    
    def _refresh_cache(self):
        """Refresh the props cache from DraftKings"""
        if self.loading:
            return
        
        self.loading = True
        try:
            # Fetch all common props
            all_props = DraftKingsAPI.get_all_common_props()
            self.cache = CachedPropsData(
                data=all_props,
                timestamp=datetime.now()
            )
        except Exception as e:
            print(f"Error fetching Vegas props: {e}")
            # Keep existing cache if fetch fails
            if not self.cache:
                self.cache = CachedPropsData(data={}, timestamp=datetime.now())
        finally:
            self.loading = False
    
    def format_prop_display(self, prop: PlayerProp) -> str:
        """Format a prop for display"""
        return f"{prop.prop_value:.1f} (O{prop.over_line}/U{prop.under_line})"
    
    def get_summary_string(self, player_name: str) -> str:
        """Get a summary string of key props for a player"""
        props = self.get_player_props(player_name)
        
        if not props:
            return ""
        
        summary_parts = []
        
        # Prioritize props based on position (we'll guess based on available props)
        if "passing_yards" in props:
            # QB
            if "passing_yards" in props:
                summary_parts.append(f"Pass: {props['passing_yards'].prop_value:.0f} yds")
            if "passing_tds" in props:
                summary_parts.append(f"TDs: {props['passing_tds'].prop_value:.1f}")
        
        if "rushing_yards" in props:
            # RB or dual-threat QB
            summary_parts.append(f"Rush: {props['rushing_yards'].prop_value:.0f} yds")
            if "rushing_tds" in props:
                summary_parts.append(f"RTDs: {props['rushing_tds'].prop_value:.1f}")
        
        if "receiving_yards" in props:
            # WR/TE/RB
            summary_parts.append(f"Rec: {props['receiving_yards'].prop_value:.0f} yds")
            if "receiving_tds" in props:
                summary_parts.append(f"RecTDs: {props['receiving_tds'].prop_value:.1f}")
            elif "receptions" in props:
                summary_parts.append(f"Recs: {props['receptions'].prop_value:.1f}")
        
        return " | ".join(summary_parts[:2])  # Limit to 2 most relevant props
    
    def _start_background_load(self):
        """Start loading props in background thread"""
        def load_and_notify():
            self._refresh_cache()
            # Notify when props are loaded
            if self.on_props_loaded and self.cache and self.cache.data:
                self.on_props_loaded()
        
        thread = threading.Thread(target=load_and_notify, daemon=True)
        thread.start()