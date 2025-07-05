#!/usr/bin/env python3
import os
import requests
from time import sleep

# All NFL team abbreviations
teams = [
    "ARZ", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE",
    "DAL", "DEN", "DET", "GB", "HOU", "IND", "JAX", "KC",
    "LA", "LAC", "LV", "MIA", "MIN", "NE", "NO", "NYG",
    "NYJ", "PHI", "PIT", "SEA", "SF", "TB", "TEN", "WAS"
]

# Create assets directory if it doesn't exist
assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "team_logos")
os.makedirs(assets_dir, exist_ok=True)

print(f"Downloading team logos to {assets_dir}")

for team in teams:
    filename = f"{team.lower()}.png"
    filepath = os.path.join(assets_dir, filename)
    
    # Skip if already downloaded
    if os.path.exists(filepath):
        print(f"✓ {team} logo already exists")
        continue
    
    url = f"https://sleepercdn.com/images/team_logos/nfl/{team.lower()}.png"
    
    try:
        print(f"Downloading {team} logo from {url}...")
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            with open(filepath, 'wb') as f:
                f.write(response.content)
            print(f"✓ {team} logo downloaded successfully")
        else:
            print(f"✗ Failed to download {team} logo: HTTP {response.status_code}")
            
        # Be nice to the server
        sleep(0.5)
        
    except Exception as e:
        print(f"✗ Error downloading {team} logo: {e}")

print("\nDone downloading team logos!")