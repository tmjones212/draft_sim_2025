import json
import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import os


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
        return response.json()
    except Exception as e:
        print(f"Error fetching ADP data: {e}")
        return None


def parse_player_data(raw_data: Dict) -> List[Dict]:
    """Parse the raw ADP data into our player format"""
    players = []
    
    if not raw_data or 'data' not in raw_data:
        return players
    
    # The data comes as a list of lists in the 'data' field
    for row in raw_data['data']:
        try:
            # Typical format: [rank, player_name, position, team, adp, etc.]
            # This may need adjustment based on actual response format
            if len(row) >= 5:
                rank = int(row[0]) if row[0] else 0
                player_name = row[1]
                position = row[2].upper()
                team = row[3]
                adp = float(row[4]) if row[4] else rank
                
                # Only include offensive positions
                if position in ['QB', 'RB', 'WR', 'TE']:
                    players.append({
                        'name': player_name,
                        'position': position,
                        'team': team,
                        'rank': rank,
                        'adp': adp
                    })
        except (IndexError, ValueError) as e:
            print(f"Error parsing player row: {e}")
            continue
    
    # Sort by rank/ADP
    players.sort(key=lambda x: x['rank'] if x['rank'] > 0 else x['adp'])
    
    # Re-rank based on sorted order
    for i, player in enumerate(players):
        player['rank'] = i + 1
    
    return players


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


def get_players_with_fallback() -> List[Dict]:
    """Get players from local file, API, or cache"""
    # Try local file first
    players = load_local_player_data()
    if players:
        return players
    
    # Try cache next
    players = load_player_cache()
    if players:
        return players
    
    # Try fetching from API
    raw_data = fetch_adp_data()
    if raw_data:
        players = parse_player_data(raw_data)
        if players:
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