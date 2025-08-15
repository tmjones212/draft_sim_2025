#!/usr/bin/env python3
"""
Unified script to fetch and aggregate NFL projections from Sleeper API.
Combines functionality of pull_projections.py and aggregate_projections.py.
"""

import requests
import json
import os
import time
import glob
from typing import List, Tuple, Dict, Any
from datetime import datetime
from collections import defaultdict

class ProjectionUpdater:
    def __init__(self):
        self.output_dir = os.path.join(os.path.dirname(__file__), "scripts", "projections_data")
        self.positions = ["QB", "RB", "WR", "TE"]
        self.weeks = range(1, 19)  # Regular season weeks 1-18
        self.projection_year = self._determine_projection_year()
        
    def _determine_projection_year(self) -> int:
        """Determine which NFL season year to fetch projections for."""
        current_year = datetime.now().year
        current_month = datetime.now().month
        
        # NFL season starts in September
        # If we're before September, use current year
        # If we're after September, use next year
        if current_month < 9:
            return current_year
        else:
            return current_year + 1
    
    def fetch_projections(self, year: int, week: int, position: str) -> List[Dict[str, Any]]:
        """Fetch projections from Sleeper API for a specific week and position."""
        url = f"https://api.sleeper.com/projections/nfl/{year}/{week}?season_type=regular&position={position.upper()}&order_by=pts_ppr"
        
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
            print(f"✓ Fetched: {year} Week {week} {position}")
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"✗ Error fetching {year} Week {week} {position}: {e}")
            return []
    
    def save_projection_file(self, projections: List[Dict[str, Any]], year: int, week: int, position: str):
        """Save projections to individual JSON file."""
        os.makedirs(self.output_dir, exist_ok=True)
        
        filename = f"{year}_{week}_{position.lower()}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(projections, f, indent=2)
    
    def fetch_all_projections(self):
        """Fetch all projections for the season."""
        print(f"\n{'='*60}")
        print(f"FETCHING {self.projection_year} NFL SEASON PROJECTIONS")
        print(f"{'='*60}")
        print(f"Positions: {', '.join(self.positions)}")
        print(f"Weeks: 1-18")
        print(f"Output: {self.output_dir}")
        print(f"{'='*60}\n")
        
        total_requests = len(self.positions) * len(self.weeks)
        completed = 0
        
        for week in self.weeks:
            print(f"\n[Week {week}]")
            for position in self.positions:
                projections = self.fetch_projections(self.projection_year, week, position)
                
                if projections:
                    self.save_projection_file(projections, self.projection_year, week, position)
                    completed += 1
                
                print(f"  Progress: {completed}/{total_requests} ({completed/total_requests*100:.1f}%)")
                time.sleep(0.5)  # Be respectful to the API
        
        print(f"\n{'='*60}")
        print(f"✓ Fetched {completed}/{total_requests} projection files")
        print(f"{'='*60}\n")
    
    def load_all_projection_files(self) -> List[Dict[str, Any]]:
        """Load all JSON projection files from the projections directory."""
        all_projections = []
        json_files = glob.glob(os.path.join(self.output_dir, "*.json"))
        
        for file_path in json_files:
            filename = os.path.basename(file_path)
            parts = filename.replace('.json', '').split('_')
            
            if len(parts) >= 3:
                year = int(parts[0])
                week = int(parts[1])
                position = parts[2].upper()
                
                with open(file_path, 'r') as f:
                    week_data = json.load(f)
                    
                    for player_data in week_data:
                        if player_data:
                            player_data['year'] = year
                            player_data['week'] = week
                            player_data['position'] = position
                            all_projections.append(player_data)
        
        return all_projections
    
    def aggregate_projections(self, projection_data: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Aggregate projections by player_id."""
        players = defaultdict(lambda: {
            'player_id': None,
            'player_name': None,
            'position': None,
            'team': None,
            'weekly_projections': [],
            'season_projection_totals': defaultdict(float),
            'weeks_projected': 0
        })
        
        for proj_entry in projection_data:
            player_id = proj_entry.get('player_id')
            if not player_id:
                continue
            
            player = players[player_id]
            
            if player['player_id'] is None:
                player['player_id'] = player_id
                
                # Get player info from nested player object or top level
                player_obj = proj_entry.get('player', {})
                player['player_name'] = (
                    player_obj.get('first_name', '') + ' ' + player_obj.get('last_name', '')
                ).strip() or proj_entry.get('player_name') or proj_entry.get('full_name') or 'Unknown'
                
                player['position'] = proj_entry.get('position', 'Unknown')
                player['team'] = proj_entry.get('team')
            
            week_proj = {
                'year': proj_entry['year'],
                'week': proj_entry['week'],
                'team': proj_entry.get('team'),
                'opponent': proj_entry.get('opponent'),
                'projections': {}
            }
            
            # Get projections from nested stats object or top level
            proj_obj = proj_entry.get('stats', proj_entry)
            
            proj_keys = [
                'pts_ppr', 'pts_std', 'pts_half_ppr',
                'pass_att', 'pass_cmp', 'pass_yd', 'pass_td', 'pass_int',
                'pass_2pt', 'pass_sack', 'pass_fd',
                'rush_att', 'rush_yd', 'rush_td', 'rush_2pt', 'rush_fd',
                'rec', 'rec_yd', 'rec_td', 'rec_2pt', 'rec_fd', 'rec_tgt',
                'fum', 'fum_lost',
                'bonus_rush_yd_100', 'bonus_rush_yd_200',
                'bonus_rec_yd_100', 'bonus_rec_yd_200',
                'bonus_pass_yd_300', 'bonus_pass_yd_400'
            ]
            
            for key in proj_keys:
                if key in proj_obj and proj_obj[key] is not None:
                    week_proj['projections'][key] = proj_obj[key]
                    player['season_projection_totals'][key] += float(proj_obj[key])
            
            if week_proj['projections']:
                player['weekly_projections'].append(week_proj)
                player['weeks_projected'] += 1
        
        for player_id, player_data in players.items():
            player_data['weekly_projections'].sort(key=lambda x: (x['year'], x['week']))
            player_data['season_projection_totals'] = dict(player_data['season_projection_totals'])
            
            # Calculate per-game averages
            if player_data['weeks_projected'] > 0:
                player_data['projection_averages'] = {}
                for stat, total in player_data['season_projection_totals'].items():
                    player_data['projection_averages'][stat] = round(total / player_data['weeks_projected'], 2)
        
        return dict(players)
    
    def save_aggregated_projections(self, aggregated_data: Dict[str, Dict[str, Any]]):
        """Save aggregated projections to JSON files."""
        # Save main aggregated file
        output_file = f"aggregated_player_projections_{self.projection_year}.json"
        output_path = os.path.join(os.path.dirname(__file__), "scripts", output_file)
        
        with open(output_path, 'w') as f:
            json.dump(aggregated_data, f, indent=2)
        
        print(f"✓ Saved: {output_path}")
        
        # Also save by position
        position_specific = defaultdict(dict)
        for player_id, player_data in aggregated_data.items():
            position = player_data['position']
            position_specific[position][player_id] = player_data
        
        for position, players in position_specific.items():
            if players:
                filename = f"aggregated_{position.lower()}_projections_{self.projection_year}.json"
                output_path = os.path.join(os.path.dirname(__file__), "scripts", filename)
                with open(output_path, 'w') as f:
                    json.dump(players, f, indent=2)
                print(f"✓ Saved: {filename}")
    
    def print_summary(self, aggregated_data: Dict[str, Dict[str, Any]]):
        """Print summary of aggregated projection data."""
        position_counts = defaultdict(int)
        total_players = len(aggregated_data)
        
        for player_data in aggregated_data.values():
            position_counts[player_data['position']] += 1
        
        print(f"\n{'='*60}")
        print(f"PROJECTION SUMMARY FOR {self.projection_year}")
        print(f"{'='*60}")
        print(f"Total unique players: {total_players}")
        print("\nPlayers by position:")
        for position, count in sorted(position_counts.items()):
            print(f"  {position}: {count}")
        
        top_scorers = sorted(
            [(p['player_name'], p['season_projection_totals'].get('pts_ppr', 0), p['position']) 
             for p in aggregated_data.values()],
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        print(f"\nTop 10 projected PPR scorers:")
        for i, (name, pts, pos) in enumerate(top_scorers, 1):
            print(f"  {i:2}. {name:<25} ({pos}): {pts:>6.1f} points")
    
    def update_web_data(self):
        """Regenerate web player data with custom ADP."""
        web_script = os.path.join(os.path.dirname(__file__), "regenerate_web_data_with_custom_adp.py")
        if os.path.exists(web_script):
            print(f"\n{'='*60}")
            print("WEB DATA UPDATE")
            print(f"{'='*60}")
            print(f"To update web data, run:")
            print(f"  python3 regenerate_web_data_with_custom_adp.py")
    
    def run(self):
        """Run the complete projection update process."""
        print("\n" + "="*60)
        print(" NFL PROJECTION UPDATER ".center(60))
        print("="*60)
        
        # Step 1: Fetch all projections
        self.fetch_all_projections()
        
        # Step 2: Load and aggregate
        print("\n" + "="*60)
        print("AGGREGATING PROJECTIONS")
        print("="*60)
        
        projection_data = self.load_all_projection_files()
        if not projection_data:
            print("✗ No projection data found!")
            return
        
        print(f"✓ Loaded {len(projection_data)} projection entries")
        
        aggregated_data = self.aggregate_projections(projection_data)
        print(f"✓ Aggregated data for {len(aggregated_data)} unique players")
        
        # Step 3: Save aggregated data
        print("\nSaving aggregated data...")
        self.save_aggregated_projections(aggregated_data)
        
        # Step 4: Print summary
        self.print_summary(aggregated_data)
        
        # Step 5: Update web data (optional)
        self.update_web_data()
        
        print(f"\n{'='*60}")
        print("✓ PROJECTION UPDATE COMPLETE!")
        print(f"{'='*60}\n")

def main():
    updater = ProjectionUpdater()
    updater.run()

if __name__ == "__main__":
    main()