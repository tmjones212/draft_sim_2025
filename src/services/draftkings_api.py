"""
DraftKings Props API - Single File Version
Easy to use in any project - just copy this file!

Usage:
    from draftkings_props_single_file import DraftKingsAPI
    
    props = DraftKingsAPI.get_passing_yards_props()
"""

import re
import requests
from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class PlayerProp:
    """Represents a player prop bet from DraftKings."""
    player_name: str
    team: str
    opponent: str
    prop_type: str
    prop_value: float
    over_line: str
    under_line: str
    
    def __repr__(self):
        return f"PlayerProp({self.player_name}, {self.prop_type}: {self.prop_value}, O{self.over_line}/U{self.under_line})"


class DraftKingsAPIException(Exception):
    """Custom exception for DraftKings API errors."""
    pass


def format_name(name):
    """Format player names for consistency."""
    # If there is a (, dump everything from there on
    name = name.split('(')[0]

    # Initial replacements and formatting
    name = name.strip().upper()
    name = re.sub(r'[,+.*]', '', name)
    name = re.sub(r'\s+(JR|SR|III|II|IV|V)$', '', name)
    name = name.replace("'", "").replace("-", " ")

    # Additional specific replacements
    replacements = {
        "MITCHELL T": "MITCH T",
        "ROBBY ANDERSON": "ROBBIE ANDERSON",
        "WILLIAM ": "WILL ",
        "OLABISI": "BISI",
        "ELI MITCHELL": "ELIJAH MITCHELL",
        "CADILLAC WILLIAMS": "CARNELL WILLIAMS",
        "GABE DAVIS": "GABRIEL DAVIS",
        "JEFFERY ": "JEFF ",
        "JOSHUA ": "JOSH ",
        "CHAUNCEY GARDNER": "CJ GARDNER",
        "BENNETT SKOWRONEK": "BEN SKOWRONEK",
        "NATHANIEL DELL": "TANK DELL",
    }

    for old, new in replacements.items():
        name = name.replace(old, new)

    # Handle specific starting names
    if name.startswith("MICHAEL "):
        name = name.replace("MICHAEL ", "MIKE ", 1)
    if name.startswith("KENNETH "):
        name = name.replace("KENNETH ", "KEN ", 1)

    return name


class DraftKingsAPI:
    """API client for fetching DraftKings NFL player props."""
    
    BASE_URL = "https://sportsbook-nash.draftkings.com/api/sportscontent/dkusnj/v1"
    _subcategories = None  # Class variable to store subcategories
    PLAYER_STATS_CATEGORY_ID = 1759  # Updated category ID for player stats

    @staticmethod
    def get_nfl_player_props(week, prop_type):
        """Legacy method - use get_nfl_player_props_2 instead."""
        return DraftKingsAPI.get_nfl_player_props_2(prop_type)

    @classmethod
    def get_nfl_player_props_2(cls, prop_type):
        """Get NFL player props for a specific prop type.
        
        Args:
            prop_type: The prop type name (e.g., "Passing Yards") or subcategory ID
            
        Returns:
            List[PlayerProp]: List of player props
        """
        subcategory_id = cls.get_subcategory_id(prop_type)
        if subcategory_id is None:
            print(f"Warning: Prop type '{prop_type}' not found in subcategories")
            return []  # Return empty list instead of raising error
        
        url = f"{cls.BASE_URL}/leagues/88808/categories/{cls.PLAYER_STATS_CATEGORY_ID}/subcategories/{subcategory_id}"
        
        headers = {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
            "origin": "https://sportsbook.draftkings.com",
            "referer": "https://sportsbook.draftkings.com/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
            "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"'
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            player_props = cls.extract_player_props(data, prop_type)
            
            return player_props
        except requests.RequestException as e:
            raise DraftKingsAPIException(f"Error fetching DraftKings data: {str(e)}")

    @staticmethod
    def extract_player_props(data, prop_type):
        """Extract player props from API response."""
        player_props = []
        
        # Create lookup dictionaries
        events_by_id = {event['id']: event for event in data.get('events', [])}
        markets_by_id = {market['id']: market for market in data.get('markets', [])}
        
        # Group selections by market and extract prop value from label
        selections_by_market = {}
        for selection in data.get('selections', []):
            market_id = selection.get('marketId')
            if market_id not in selections_by_market:
                selections_by_market[market_id] = []
            selections_by_market[market_id].append(selection)
        
        # Process each market
        for market_id, selections in selections_by_market.items():
            market = markets_by_id.get(market_id, {})
            event_id = market.get('eventId')
            event = events_by_id.get(event_id, {})
            
            # Extract player name from event name (e.g., "NFL 2025/26 - Josh Allen")
            event_name = event.get('name', '')
            player_name = ''
            if ' - ' in event_name:
                player_name = event_name.split(' - ', 1)[1]
            
            # Format the player name
            player_name = format_name(player_name)
            
            # Get team info from participants
            participants = event.get('participants', [])
            team = ''
            
            # Check both participants for team info (could be in either position)
            for participant in participants:
                if participant.get('type') == 'Team' and 'metadata' in participant:
                    team = participant.get('metadata', {}).get('rosettaTeamName', '')
                    if team:
                        break
            
            # Find over/under selections
            over_selection = None
            under_selection = None
            prop_value = 0.0
            
            for selection in selections:
                outcome_type = selection.get('outcomeType', '')
                if outcome_type == 'Over':
                    over_selection = selection
                    # Extract prop value from label (e.g., "Over 1150.5" -> 1150.5)
                    label = selection.get('label', '')
                    try:
                        prop_value = float(label.replace('Over ', ''))
                    except:
                        prop_value = 0.0
                elif outcome_type == 'Under':
                    under_selection = selection
            
            if over_selection and player_name:
                over_line = over_selection.get('displayOdds', {}).get('american', '')
                under_line = under_selection.get('displayOdds', {}).get('american', '') if under_selection else ''
                
                player_prop = PlayerProp(
                    player_name=player_name,
                    team=team,
                    opponent='',  # Not available in this data
                    prop_type=prop_type,
                    prop_value=prop_value,
                    over_line=over_line,
                    under_line=under_line
                )
                player_props.append(player_prop)

        return player_props

    @classmethod
    def get_subcategory_id(cls, prop_type):
        """Get subcategory ID from prop type name or ID."""
        if cls._subcategories is None:
            cls._subcategories = cls.get_all_subcategories()
        
        if isinstance(prop_type, int):
            # If the identifier is an integer, assume it's already an ID
            for subcategory in cls._subcategories:
                if subcategory['id'] == prop_type:
                    return subcategory['id']
        elif isinstance(prop_type, str):
            # If the identifier is a string, search by name
            for subcategory in cls._subcategories:
                if subcategory['name'].lower() == prop_type.lower():
                    return subcategory['id']
        
        return None  # Return None if subcategory not found

    @classmethod
    def get_all_subcategories(cls):
        """Get all available subcategories."""
        if cls._subcategories is not None:
            return cls._subcategories

        # Get all subcategories for the player stats category
        url = f"{cls.BASE_URL}/leagues/88808/categories/{cls.PLAYER_STATS_CATEGORY_ID}"
        
        headers = {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
            "origin": "https://sportsbook.draftkings.com",
            "referer": "https://sportsbook.draftkings.com/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
            "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"'
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            cls._subcategories = [
                {
                    'id': sub['id'],
                    'categoryId': sub['categoryId'],
                    'name': sub['name'],
                    'componentId': sub['componentId'],
                    'sortOrder': sub['sortOrder'],
                    'tags': sub.get('tags', [])
                }
                for sub in data.get('subcategories', [])
            ]
            
            return cls._subcategories
        except requests.RequestException as e:
            raise DraftKingsAPIException(f"Error fetching DraftKings subcategories: {str(e)}")

    # Individual prop type methods for better discoverability
    @classmethod
    def get_passing_yards_props(cls):
        """Get NFL player passing yards season-long props from DraftKings.
        
        Returns:
            List[PlayerProp]: List of player props with passing yards lines
        """
        return cls.get_nfl_player_props_2("Passing Yards")
    
    @classmethod
    def get_passing_tds_props(cls):
        """Get NFL player passing touchdowns season-long props from DraftKings.
        
        Returns:
            List[PlayerProp]: List of player props with passing TD lines
        """
        return cls.get_nfl_player_props_2("Passing TDs")
    
    @classmethod
    def get_rushing_yards_props(cls):
        """Get NFL player rushing yards season-long props from DraftKings.
        
        Returns:
            List[PlayerProp]: List of player props with rushing yards lines
        """
        return cls.get_nfl_player_props_2("Rushing Yards")
    
    @classmethod
    def get_rushing_tds_props(cls):
        """Get NFL player rushing touchdowns season-long props from DraftKings.
        
        Returns:
            List[PlayerProp]: List of player props with rushing TD lines
        """
        return cls.get_nfl_player_props_2("Rushing TDs")
    
    @classmethod
    def get_receiving_yards_props(cls):
        """Get NFL player receiving yards season-long props from DraftKings.
        
        Returns:
            List[PlayerProp]: List of player props with receiving yards lines
        """
        return cls.get_nfl_player_props_2("Receiving Yards")
    
    @classmethod
    def get_receiving_tds_props(cls):
        """Get NFL player receiving touchdowns season-long props from DraftKings.
        
        Returns:
            List[PlayerProp]: List of player props with receiving TD lines
        """
        return cls.get_nfl_player_props_2("Receiving TDs")
    
    @classmethod
    def get_receptions_props(cls):
        """Get NFL player receptions season-long props from DraftKings.
        
        Returns:
            List[PlayerProp]: List of player props with reception lines
        """
        return cls.get_nfl_player_props_2("Receptions")
    
    @classmethod
    def get_interceptions_thrown_props(cls):
        """Get NFL player interceptions thrown season-long props from DraftKings.
        
        Returns:
            List[PlayerProp]: List of player props with interceptions thrown lines
        """
        return cls.get_nfl_player_props_2("Passing Interceptions")
    
    @classmethod
    def get_sacks_props(cls):
        """Get NFL player sacks season-long props from DraftKings.
        
        Returns:
            List[PlayerProp]: List of player props with sacks lines
        """
        return cls.get_nfl_player_props_2("Sacks")
    
    @classmethod
    def get_kicking_points_props(cls):
        """Get NFL kicker points season-long props from DraftKings.
        
        Returns:
            List[PlayerProp]: List of player props with kicking points lines
        """
        return cls.get_nfl_player_props_2("Kicking Points")
    
    @classmethod
    def get_all_common_props(cls):
        """Get all common NFL player props from DraftKings.
        
        Returns a dictionary with prop type as key and list of PlayerProps as value.
        Includes: passing yards/TDs, rushing yards/TDs, receiving yards/TDs, receptions.
        
        Returns:
            Dict[str, List[PlayerProp]]: Dictionary of prop types to player props
        """
        return {
            "passing_yards": cls.get_passing_yards_props(),
            "passing_tds": cls.get_passing_tds_props(),
            "rushing_yards": cls.get_rushing_yards_props(),
            "rushing_tds": cls.get_rushing_tds_props(),
            "receiving_yards": cls.get_receiving_yards_props(),
            "receiving_tds": cls.get_receiving_tds_props(),
            "receptions": cls.get_receptions_props()
        }


# Example usage if running this file directly
if __name__ == "__main__":
    # Example: Get passing yards props
    props = DraftKingsAPI.get_passing_yards_props()
    print(f"Found {len(props)} passing yards props")
    for prop in props[:5]:
        print(f"{prop.player_name} ({prop.team}): {prop.prop_value} yards")
        print(f"  Over: {prop.over_line}, Under: {prop.under_line}")