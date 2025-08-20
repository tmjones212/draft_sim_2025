import json
import os
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from src.utils.player_extensions import format_name

class NFCADPFetcher:
    def __init__(self):
        self.data_dir = "data"
        self.nfc_adp_file = os.path.join(self.data_dir, "nfc_adp.json")
        
    def fetch_nfc_adp(self):
        """Fetch NFC ADP data from the website for the last 3 days"""
        # Calculate date range (last 3 days)
        to_date = datetime.now()
        from_date = to_date - timedelta(days=3)
        
        # Format dates as YYYY-MM-DD
        from_date_str = from_date.strftime("%Y-%m-%d")
        to_date_str = to_date.strftime("%Y-%m-%d")
        
        url = "https://nfc.shgn.com/adp.data.php"
        
        headers = {
            "accept": "text/html, */*; q=0.01",
            "accept-language": "en-US,en;q=0.9",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "origin": "https://nfc.shgn.com",
            "referer": "https://nfc.shgn.com/adp/football",
            "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
            "x-requested-with": "XMLHttpRequest"
        }
        
        data = {
            "team_id": "0",
            "from_date": from_date_str,
            "to_date": to_date_str,
            "num_teams": "0",
            "draft_type": "0",
            "sport": "football",
            "position": "",
            "league_teams": "0"
        }
        
        try:
            response = requests.post(url, headers=headers, data=data)
            response.raise_for_status()
            
            # Parse HTML response
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all player rows
            player_rows = soup.find_all('tr')
            
            nfc_adp_data = {}
            
            for row in player_rows:
                tds = row.find_all('td')
                if len(tds) >= 4:  # Make sure we have enough columns
                    # Check if first td has a player link
                    player_link = None
                    for td in tds[:2]:  # Check first two tds for player link
                        link = td.find('a', class_='PlayerLinkV')
                        if link:
                            player_link = link
                            break
                    
                    if player_link:
                        # Get the player name from the link text
                        player_name = player_link.get_text(strip=True)
                        
                        # Format the name using the format_name function
                        formatted_name = format_name(player_name)
                        
                        # Find the td with ADP value (has sort-value attribute)
                        adp_value = None
                        for td in tds:
                            sort_val = td.get('sort-value', '')
                            # Look for decimal values that look like ADP (e.g., 1.12, 2.54)
                            if sort_val and '.' in sort_val:
                                try:
                                    val = float(sort_val)
                                    if 0 < val < 500:  # Reasonable ADP range
                                        adp_value = val
                                        break
                                except ValueError:
                                    pass
                        
                        if adp_value:
                            nfc_adp_data[formatted_name] = adp_value
            
            # Save to JSON file
            os.makedirs(self.data_dir, exist_ok=True)
            with open(self.nfc_adp_file, 'w') as f:
                json.dump({
                    'last_updated': datetime.now().isoformat(),
                    'from_date': from_date_str,
                    'to_date': to_date_str,
                    'adp_data': nfc_adp_data
                }, f, indent=2)
            
            return nfc_adp_data
            
        except Exception as e:
            print(f"Error fetching NFC ADP data: {e}")
            return None
    
    def load_nfc_adp(self):
        """Load NFC ADP data from saved file"""
        if os.path.exists(self.nfc_adp_file):
            try:
                with open(self.nfc_adp_file, 'r') as f:
                    data = json.load(f)
                    return data.get('adp_data', {})
            except Exception as e:
                print(f"Error loading NFC ADP data: {e}")
        return {}
    
    def get_player_nfc_adp(self, player_name):
        """Get NFC ADP for a specific player"""
        nfc_adp_data = self.load_nfc_adp()
        formatted_name = format_name(player_name)
        return nfc_adp_data.get(formatted_name, None)