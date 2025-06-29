import json
import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import os
from .player_extensions import format_name


def fetch_adp_data() -> Optional[Dict]:
    """Fetch ADP data from nfc.shgn.com"""
    url = "https://nfc.shgn.com/adp.data.php"
    
    # Calculate date range (last 2 weeks)
    to_date = datetime.now()
    from_date = to_date - timedelta(days=14)
    
    headers = {
        "accept": "text/html, */*; q=0.01",
        "accept-language": "en-US,en;q=0.9",
        "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        "origin": "https://nfc.shgn.com",
        "referer": "https://nfc.shgn.com/adp/football",
        "sec-ch-ua": '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        "x-requested-with": "XMLHttpRequest"
    }
    
    data = {
        "team_id": "0",
        "from_date": from_date.strftime("%Y-%m-%d"),
        "to_date": to_date.strftime("%Y-%m-%d"),
        "num_teams": "0",
        "draft_type": "0",
        "sport": "football",
        "position": "",
        "league_teams": "0"
    }
    
    try:
        response = requests.post(url, headers=headers, data=data, timeout=10)
        response.raise_for_status()
        # Return the text content for HTML parsing
        return response.text
    except Exception as e:
        print(f"Error fetching ADP data: {e}")
        return None


def parse_player_data(raw_data: str) -> List[Dict]:
    """Parse the HTML ADP data into our player format"""
    import re
    from html.parser import HTMLParser
    
    class ADPHTMLParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.players = []
            self.current_player = {}
            self.in_rank = False
            self.in_player_link = False
            self.current_data = ""
            
        def handle_starttag(self, tag, attrs):
            attrs_dict = dict(attrs)
            
            if tag == "span" and attrs_dict.get("class") == "rank":
                self.in_rank = True
            elif tag == "a" and "PlayerLinkV" in attrs_dict.get("class", ""):
                self.in_player_link = True
                # Extract player name from href
                href = attrs_dict.get("href", "")
                if href:
                    parts = href.split("/")
                    if len(parts) > 0:
                        name = parts[-1].replace("%20", " ").replace("%27", "'")
                        self.current_player["name"] = name
            elif tag == "tr":
                # Extract position from filter-pos attribute
                filter_pos = attrs_dict.get("filter-pos", "")
                if filter_pos:
                    # Get first position (primary position)
                    pos = filter_pos.split(",")[0]
                    if pos in ["QB", "RB", "WR", "TE"]:
                        self.current_player["position"] = pos
                # Extract team
                filter_team = attrs_dict.get("filter-team", "")
                if filter_team:
                    self.current_player["team"] = filter_team
                    
        def handle_data(self, data):
            if self.in_rank:
                try:
                    self.current_player["rank"] = int(data.strip())
                except:
                    pass
                    
        def handle_endtag(self, tag):
            if tag == "span" and self.in_rank:
                self.in_rank = False
            elif tag == "a" and self.in_player_link:
                self.in_player_link = False
            elif tag == "tr" and self.current_player:
                if all(k in self.current_player for k in ["rank", "name", "position"]):
                    self.players.append(self.current_player)
                self.current_player = {}
    
    # If it's already a dict (JSON response), return empty
    if isinstance(raw_data, dict):
        return []
    
    # Parse HTML
    parser = ADPHTMLParser()
    parser.feed(raw_data)
    
    # Extract ADP values from the HTML using regex
    adp_pattern = r'<td class="numeric">(\d+\.\d+)</td>'
    adp_values = re.findall(adp_pattern, raw_data)
    
    # Match ADP values to players
    for i, player in enumerate(parser.players):
        if i < len(adp_values):
            player['adp'] = float(adp_values[i])
        else:
            player['adp'] = player['rank']
    
    return parser.players[:150]  # Return top 150


def save_player_cache(players: List[Dict], cache_file: str = "player_cache.json"):
    """Save player data to cache file"""
    cache_path = os.path.join(os.path.dirname(__file__), cache_file)
    cache_data = {
        'timestamp': datetime.now().isoformat(),
        'players': players
    }
    
    try:
        with open(cache_path, 'w') as f:
            json.dump(cache_data, f, indent=2)
        print(f"Saved {len(players)} players to cache")
    except Exception as e:
        print(f"Error saving player cache: {e}")


def load_player_cache(cache_file: str = "player_cache.json", max_age_hours: int = 24) -> Optional[List[Dict]]:
    """Load player data from cache if it exists and is recent"""
    cache_path = os.path.join(os.path.dirname(__file__), cache_file)
    
    if not os.path.exists(cache_path):
        return None
    
    try:
        with open(cache_path, 'r') as f:
            cache_data = json.load(f)
        
        # Check cache age
        cache_time = datetime.fromisoformat(cache_data['timestamp'])
        if datetime.now() - cache_time > timedelta(hours=max_age_hours):
            print("Cache is too old, will fetch fresh data")
            return None
        
        print(f"Loaded {len(cache_data['players'])} players from cache")
        return cache_data['players']
    except Exception as e:
        print(f"Error loading player cache: {e}")
        return None


def load_local_player_data() -> Optional[List[Dict]]:
    """Load player data from local JSON file"""
    local_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'players_2025.json')
    
    try:
        with open(local_file, 'r') as f:
            data = json.load(f)
        print(f"Loaded {len(data['players'])} players from local file")
        return data['players']
    except Exception as e:
        print(f"Error loading local player data: {e}")
        return None


def load_sleeper_players() -> Dict[str, Dict]:
    """Load the Sleeper player database"""
    try:
        # Look for the players.json file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        players_file = os.path.join(project_root, 'data', 'players.json')
        
        print(f"DEBUG: Looking for players.json at {players_file}")
        if os.path.exists(players_file):
            print(f"DEBUG: Found players.json")
            with open(players_file, 'r') as f:
                sleeper_data = json.load(f)
                # Create a name-to-player mapping for faster lookups
                name_to_player = {}
                fantasy_positions = ['QB', 'RB', 'WR', 'TE', 'K', 'DEF']
                for player_id, player_data in sleeper_data.items():
                    if 'name' in player_data and player_data.get('position') in fantasy_positions:
                        name = player_data['name']
                        # Store the player data with ID
                        name_to_player[name] = {
                            'player_id': player_id,
                            'team': player_data.get('team'),
                            'full_name': player_data.get('full_name'),
                            'position': player_data.get('position')
                        }
                
                # Print some sample names to debug
                sample_names = list(name_to_player.keys())[:5]
                print(f"DEBUG: Sample player names from Sleeper: {sample_names}")
                return name_to_player
        else:
            print(f"DEBUG: players.json not found at {players_file}")
    except Exception as e:
        print(f"Error loading Sleeper players: {e}")
    return {}


def match_with_sleeper_data(players: List[Dict]) -> List[Dict]:
    """Match ADP players with Sleeper player IDs"""
    sleeper_players = load_sleeper_players()
    print(f"DEBUG: Loaded {len(sleeper_players)} players from Sleeper data")
    
    matched_count = 0
    for player in players:
        # Format the name to match Sleeper format
        formatted_name = format_name(player['name'])
        
        # Look up in Sleeper data
        if formatted_name in sleeper_players:
            sleeper_data = sleeper_players[formatted_name]
            player['player_id'] = sleeper_data['player_id']
            matched_count += 1
            # Update team if not already set
            if not player.get('team') and sleeper_data.get('team'):
                player['team'] = sleeper_data['team']
        else:
            # Try the original name too
            if player['name'] in sleeper_players:
                sleeper_data = sleeper_players[player['name']]
                player['player_id'] = sleeper_data['player_id']
                matched_count += 1
                if not player.get('team') and sleeper_data.get('team'):
                    player['team'] = sleeper_data['team']
            else:
                print(f"DEBUG: No match for player: {player['name']} (formatted: {formatted_name})")
    
    print(f"DEBUG: Matched {matched_count} out of {len(players)} players with Sleeper IDs")
    return players


def get_players_with_fallback() -> List[Dict]:
    """Get players from local file, API, or cache"""
    # Try local file first
    players = load_local_player_data()
    if players:
        # Match with Sleeper data to get player IDs
        return match_with_sleeper_data(players)
    
    # Try cache next
    players = load_player_cache()
    if players:
        # Match with Sleeper data if not already matched
        if players and 'player_id' not in players[0]:
            players = match_with_sleeper_data(players)
        return players
    
    # Try fetching from API
    raw_data = fetch_adp_data()
    if raw_data:
        players = parse_player_data(raw_data)
        if players:
            # Match with Sleeper data to get player IDs
            players = match_with_sleeper_data(players)
            save_player_cache(players)
            return players
    
    # Fallback to basic data
    print("Using fallback player data")
    return [
        {'name': 'Justin Jefferson', 'position': 'WR', 'team': 'MIN', 'rank': 1, 'adp': 1.2},
        {'name': 'CeeDee Lamb', 'position': 'WR', 'team': 'DAL', 'rank': 2, 'adp': 2.1},
        {'name': 'Tyreek Hill', 'position': 'WR', 'team': 'MIA', 'rank': 3, 'adp': 3.5},
        {'name': 'Amon-Ra St. Brown', 'position': 'WR', 'team': 'DET', 'rank': 4, 'adp': 4.8},
        {'name': 'Bijan Robinson', 'position': 'RB', 'team': 'ATL', 'rank': 5, 'adp': 5.2},
        {'name': 'Ja\'Marr Chase', 'position': 'WR', 'team': 'CIN', 'rank': 6, 'adp': 6.1},
        {'name': 'Breece Hall', 'position': 'RB', 'team': 'NYJ', 'rank': 7, 'adp': 7.3},
        {'name': 'A.J. Brown', 'position': 'WR', 'team': 'PHI', 'rank': 8, 'adp': 8.0},
        {'name': 'Christian McCaffrey', 'position': 'RB', 'team': 'SF', 'rank': 9, 'adp': 8.5},
        {'name': 'Puka Nacua', 'position': 'WR', 'team': 'LAR', 'rank': 10, 'adp': 10.2},
        {'name': 'Garrett Wilson', 'position': 'WR', 'team': 'NYJ', 'rank': 11, 'adp': 11.5},
        {'name': 'Jonathan Taylor', 'position': 'RB', 'team': 'IND', 'rank': 12, 'adp': 12.3},
        {'name': 'Saquon Barkley', 'position': 'RB', 'team': 'PHI', 'rank': 13, 'adp': 13.1},
        {'name': 'Chris Olave', 'position': 'WR', 'team': 'NO', 'rank': 14, 'adp': 14.7},
        {'name': 'Marvin Harrison Jr.', 'position': 'WR', 'team': 'ARI', 'rank': 15, 'adp': 15.2},
        {'name': 'Davante Adams', 'position': 'WR', 'team': 'NYJ', 'rank': 16, 'adp': 16.8},
        {'name': 'Travis Etienne Jr.', 'position': 'RB', 'team': 'JAX', 'rank': 17, 'adp': 17.5},
        {'name': 'Jahmyr Gibbs', 'position': 'RB', 'team': 'DET', 'rank': 18, 'adp': 18.3},
        {'name': 'Kyren Williams', 'position': 'RB', 'team': 'LAR', 'rank': 19, 'adp': 19.1},
        {'name': 'De\'Von Achane', 'position': 'RB', 'team': 'MIA', 'rank': 20, 'adp': 20.5},
        {'name': 'Josh Allen', 'position': 'QB', 'team': 'BUF', 'rank': 21, 'adp': 21.2},
        {'name': 'Jalen Hurts', 'position': 'QB', 'team': 'PHI', 'rank': 22, 'adp': 22.8},
        {'name': 'Sam LaPorta', 'position': 'TE', 'team': 'DET', 'rank': 23, 'adp': 23.5},
        {'name': 'Mike Evans', 'position': 'WR', 'team': 'TB', 'rank': 24, 'adp': 24.3},
        {'name': 'Stefon Diggs', 'position': 'WR', 'team': 'HOU', 'rank': 25, 'adp': 25.1},
    ]