#!/usr/bin/env python3
import json
import os
from collections import defaultdict
from typing import Dict, List, Any
import glob
from datetime import datetime

def load_projection_files(projections_dir: str = "projections_data") -> List[Dict[str, Any]]:
    """Load all JSON projection files from the projections directory."""
    all_projections = []
    projections_path = os.path.join(os.path.dirname(__file__), projections_dir)
    
    json_files = glob.glob(os.path.join(projections_path, "*.json"))
    
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

def aggregate_by_player(projection_data: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
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

def save_aggregated_projections(aggregated_data: Dict[str, Dict[str, Any]], year: int):
    """Save aggregated projections to JSON file."""
    output_file = f"aggregated_player_projections_{year}.json"
    output_path = os.path.join(os.path.dirname(__file__), output_file)
    
    with open(output_path, 'w') as f:
        json.dump(aggregated_data, f, indent=2)
    
    print(f"Saved aggregated projections to: {output_path}")
    
    # Also save by position
    position_specific = defaultdict(dict)
    for player_id, player_data in aggregated_data.items():
        position = player_data['position']
        position_specific[position][player_id] = player_data
    
    for position, players in position_specific.items():
        if players:
            filename = f"aggregated_{position.lower()}_projections_{year}.json"
            output_path = os.path.join(os.path.dirname(__file__), filename)
            with open(output_path, 'w') as f:
                json.dump(players, f, indent=2)
            print(f"Saved: {filename}")

def print_summary(aggregated_data: Dict[str, Dict[str, Any]], year: int):
    """Print summary of aggregated projection data."""
    position_counts = defaultdict(int)
    total_players = len(aggregated_data)
    
    for player_data in aggregated_data.values():
        position_counts[player_data['position']] += 1
    
    print(f"\nProjection Aggregation Summary for {year}:")
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
    
    print(f"\nTop 10 projected PPR scorers for {year}:")
    for i, (name, pts, pos) in enumerate(top_scorers, 1):
        print(f"  {i}. {name} ({pos}): {pts:.1f} points")

def main():
    # Determine year for projections
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    # If we're before September, current season is this year
    # If we're after September, projections are for next year
    if current_month < 9:
        projection_year = current_year
    else:
        projection_year = current_year + 1
    
    print(f"Loading projection files for {projection_year} season...")
    projection_data = load_projection_files()
    
    if not projection_data:
        print("No projection data found. Make sure to run pull_projections.py first.")
        return
    
    print(f"Loaded {len(projection_data)} projection entries")
    
    print("\nAggregating by player_id...")
    aggregated_data = aggregate_by_player(projection_data)
    
    print_summary(aggregated_data, projection_year)
    
    print("\nSaving aggregated projection data...")
    save_aggregated_projections(aggregated_data, projection_year)
    
    print("\nProjection aggregation complete!")

if __name__ == "__main__":
    main()