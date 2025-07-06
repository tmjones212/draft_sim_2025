#!/usr/bin/env python3
import requests
import json
import os
import time
from typing import List, Tuple, Dict, Any

class StatRequestParameters:
    def __init__(self, year: int, week: int, position: str, stat_type: str = "stats"):
        self.year = year
        self.week = week
        self.position = position
        self.stat_type = stat_type

def get_json_from_api_call(stat_request_parameter: StatRequestParameters) -> Tuple[List[Dict[str, Any]], StatRequestParameters]:
    stat_type_string = stat_request_parameter.stat_type
    
    url = f"https://api.sleeper.com/{stat_type_string}/nfl/{stat_request_parameter.year}/{stat_request_parameter.week}?season_type=regular&position={stat_request_parameter.position.upper()}&order_by=pts_ppr"
    
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
        
        print(f"Fetched: {stat_request_parameter.year} Week {stat_request_parameter.week} {stat_request_parameter.position}")
        
        stats = response.json()
        return (stats, stat_request_parameter)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data for {stat_request_parameter.year} Week {stat_request_parameter.week} {stat_request_parameter.position}: {e}")
        return ([], stat_request_parameter)

def save_stats_to_json(stats: List[Dict[str, Any]], params: StatRequestParameters, output_dir: str = "stats_data"):
    os.makedirs(output_dir, exist_ok=True)
    
    filename = f"{params.year}_{params.week}_{params.position.lower()}.json"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w') as f:
        json.dump(stats, f, indent=2)
    
    print(f"Saved: {filepath}")

def main():
    year = 2024
    positions = ["QB", "RB", "WR", "TE", "DB", "LB"]
    weeks = range(1, 19)
    
    output_dir = os.path.join(os.path.dirname(__file__), "stats_data")
    
    total_requests = len(positions) * len(weeks)
    completed = 0
    
    print(f"Starting to fetch {total_requests} stat files for {year} season...")
    print(f"Positions: {', '.join(positions)}")
    print(f"Weeks: 1-18")
    print("-" * 50)
    
    for week in weeks:
        for position in positions:
            # Check if file already exists
            filename = f"{year}_{week}_{position.lower()}.json"
            filepath = os.path.join(output_dir, filename)
            
            if os.path.exists(filepath):
                print(f"Skipping: {filepath} (already exists)")
                completed += 1
                continue
            
            params = StatRequestParameters(year, week, position)
            stats, params = get_json_from_api_call(params)
            
            if stats:
                save_stats_to_json(stats, params, output_dir)
                completed += 1
                print(f"Progress: {completed}/{total_requests} ({completed/total_requests*100:.1f}%)")
            
            time.sleep(0.5)
        
        print(f"Completed Week {week}")
        print("-" * 30)
    
    print(f"\nAll done! Fetched {completed} stat files.")
    print(f"Stats saved in: {output_dir}")

if __name__ == "__main__":
    main()