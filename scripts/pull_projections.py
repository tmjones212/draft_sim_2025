#!/usr/bin/env python3
import requests
import json
import os
import time
from typing import List, Tuple, Dict, Any
from datetime import datetime

class ProjectionRequestParameters:
    def __init__(self, year: int, week: int, position: str):
        self.year = year
        self.week = week
        self.position = position

def get_json_from_api_call(params: ProjectionRequestParameters) -> Tuple[List[Dict[str, Any]], ProjectionRequestParameters]:
    # Using "projections" instead of "stats" in the URL
    url = f"https://api.sleeper.com/projections/nfl/{params.year}/{params.week}?season_type=regular&position={params.position.upper()}&order_by=pts_ppr"
    
    headers = {
        "authority": "api.sleeper.com",
        "accept": "application/json",
        "accept-language": "en-US,en;q=0.9",
        "origin": "https://sleeper.com",
        "referer": "https://sleeper.com/",
        "sec-ch-ua": '"Chromium";v="106", "Google"',
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        print(f"Fetched projections: {params.year} Week {params.week} {params.position}")
        
        projections = response.json()
        return (projections, params)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching projections for {params.year} Week {params.week} {params.position}: {e}")
        return ([], params)

def save_projections_to_json(projections: List[Dict[str, Any]], params: ProjectionRequestParameters, output_dir: str = "projections_data"):
    os.makedirs(output_dir, exist_ok=True)
    
    filename = f"{params.year}_{params.week}_{params.position.lower()}.json"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w') as f:
        json.dump(projections, f, indent=2)
    
    print(f"Saved: {filepath}")

def main():
    # Get current year
    current_year = datetime.now().year
    
    # Determine NFL season year
    # NFL season starts in September, so if we're before September, use previous year
    current_month = datetime.now().month
    if current_month < 9:
        season_year = current_year - 1
    else:
        season_year = current_year
    
    # For 2025 projections, we want to look ahead
    projection_year = season_year + 1
    
    print(f"Fetching projections for {projection_year} NFL season")
    
    positions = ["QB", "RB", "WR", "TE", "DB", "LB"]
    weeks = range(1, 19)  # Regular season weeks 1-18
    
    output_dir = os.path.join(os.path.dirname(__file__), "projections_data")
    
    total_requests = len(positions) * len(weeks)
    completed = 0
    
    print(f"Starting to fetch {total_requests} projection files for {projection_year} season...")
    print(f"Positions: {', '.join(positions)}")
    print(f"Weeks: 1-18")
    print("-" * 50)
    
    for week in weeks:
        for position in positions:
            # Check if file already exists
            filename = f"{projection_year}_{week}_{position.lower()}.json"
            filepath = os.path.join(output_dir, filename)
            
            if os.path.exists(filepath):
                print(f"Skipping: {filepath} (already exists)")
                completed += 1
                continue
            
            params = ProjectionRequestParameters(projection_year, week, position)
            projections, params = get_json_from_api_call(params)
            
            if projections:
                save_projections_to_json(projections, params, output_dir)
                completed += 1
                print(f"Progress: {completed}/{total_requests} ({completed/total_requests*100:.1f}%)")
            
            # Be respectful to the API
            time.sleep(0.5)
        
        print(f"Completed Week {week}")
        print("-" * 30)
    
    print(f"\nAll done! Fetched {completed} projection files.")
    print(f"Projections saved in: {output_dir}")

if __name__ == "__main__":
    main()