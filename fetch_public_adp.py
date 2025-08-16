#!/usr/bin/env python3
"""
Fetch public ADP data from FantasyFootballCalculator API and save it for offline use.
"""

import json
import requests
from src.utils.player_extensions import format_name

def fetch_public_adp():
    """Fetch public ADP data from the API."""
    url = "https://fantasyfootballcalculator.com/api/v1/adp/ppr"
    params = {
        "teams": 10,
        "year": 2025,
        "position": "all"
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") == "Success" and data.get("players"):
            print(f"Successfully fetched {len(data['players'])} players")
            
            # Format player names to match our system
            for player in data["players"]:
                player["formatted_name"] = format_name(player["name"])
            
            # Save to web_static directory
            output_path = "web_static/public_adp.json"
            with open(output_path, "w") as f:
                json.dump(data, f, indent=2)
            
            print(f"Saved public ADP data to {output_path}")
            return data
        else:
            print("API returned unexpected format")
            return None
            
    except Exception as e:
        print(f"Error fetching public ADP: {e}")
        return None

if __name__ == "__main__":
    fetch_public_adp()