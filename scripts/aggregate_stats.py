#!/usr/bin/env python3
import json
import os
from collections import defaultdict
from typing import Dict, List, Any
import glob

def load_stats_files(stats_dir: str = "stats_data") -> List[Dict[str, Any]]:
    """Load all JSON stats files from the stats directory."""
    all_stats = []
    stats_path = os.path.join(os.path.dirname(__file__), stats_dir)
    
    json_files = glob.glob(os.path.join(stats_path, "*.json"))
    
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
                        all_stats.append(player_data)
    
    return all_stats

def aggregate_by_player(stats_data: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Aggregate stats by player_id."""
    players = defaultdict(lambda: {
        'player_id': None,
        'player_name': None,
        'position': None,
        'team': None,
        'weekly_stats': [],
        'season_totals': defaultdict(float),
        'games_played': 0
    })
    
    for stat_entry in stats_data:
        player_id = stat_entry.get('player_id')
        if not player_id:
            continue
        
        player = players[player_id]
        
        if player['player_id'] is None:
            player['player_id'] = player_id
            
            # Get player info from nested player object or top level
            player_obj = stat_entry.get('player', {})
            player['player_name'] = (
                player_obj.get('first_name', '') + ' ' + player_obj.get('last_name', '')
            ).strip() or stat_entry.get('player_name') or stat_entry.get('full_name') or 'Unknown'
            
            player['position'] = stat_entry.get('position', 'Unknown')
            player['team'] = stat_entry.get('team')
        
        week_stat = {
            'year': stat_entry['year'],
            'week': stat_entry['week'],
            'team': stat_entry.get('team'),
            'opponent': stat_entry.get('opponent'),
            'stats': {}
        }
        
        # Get stats from nested stats object or top level
        stats_obj = stat_entry.get('stats', stat_entry)
        
        stat_keys = [
            'pts_ppr', 'pts_std', 'pts_half_ppr',
            'pass_att', 'pass_cmp', 'pass_yd', 'pass_td', 'pass_int',
            'pass_2pt', 'pass_sack', 'pass_fd',
            'rush_att', 'rush_yd', 'rush_td', 'rush_2pt', 'rush_fd',
            'rec', 'rec_yd', 'rec_td', 'rec_2pt', 'rec_fd', 'rec_tgt',
            'fum', 'fum_lost',
            'bonus_rush_yd_100', 'bonus_rush_yd_200',
            'bonus_rec_yd_100', 'bonus_rec_yd_200',
            'bonus_pass_yd_300', 'bonus_pass_yd_400',
            'off_snp',  # Offensive snap count
            # IDP stats for DB and LB
            'def_snp',  # Defensive snap count
            'idp_tkl', 'idp_tkl_solo', 'idp_tkl_ast', 'idp_tkl_loss',
            'idp_sack', 'idp_qb_hit', 'idp_int', 'idp_pass_def',
            'idp_ff', 'idp_fum_rec', 'idp_def_td', 'idp_safety',
            'idp_blk', 'idp_tkl_miss'
        ]
        
        for key in stat_keys:
            if key in stats_obj and stats_obj[key] is not None:
                week_stat['stats'][key] = stats_obj[key]
                player['season_totals'][key] += float(stats_obj[key])
        
        if week_stat['stats']:
            player['weekly_stats'].append(week_stat)
            player['games_played'] += 1
    
    for player_id, player_data in players.items():
        player_data['weekly_stats'].sort(key=lambda x: (x['year'], x['week']))
        player_data['season_totals'] = dict(player_data['season_totals'])
        
        if player_data['games_played'] > 0:
            player_data['averages'] = {}
            for stat, total in player_data['season_totals'].items():
                player_data['averages'][stat] = round(total / player_data['games_played'], 2)
    
    return dict(players)

def save_aggregated_stats(aggregated_data: Dict[str, Dict[str, Any]], output_file: str):
    """Save aggregated stats to JSON file."""
    output_path = os.path.join(os.path.dirname(__file__), output_file)
    
    with open(output_path, 'w') as f:
        json.dump(aggregated_data, f, indent=2)
    
    print(f"Saved aggregated stats to: {output_path}")

def print_summary(aggregated_data: Dict[str, Dict[str, Any]]):
    """Print summary of aggregated data."""
    position_counts = defaultdict(int)
    total_players = len(aggregated_data)
    
    for player_data in aggregated_data.values():
        position_counts[player_data['position']] += 1
    
    print("\nAggregation Summary:")
    print(f"Total unique players: {total_players}")
    print("\nPlayers by position:")
    for position, count in sorted(position_counts.items()):
        print(f"  {position}: {count}")
    
    top_scorers = sorted(
        [(p['player_name'], p['season_totals'].get('pts_ppr', 0), p['position']) 
         for p in aggregated_data.values()],
        key=lambda x: x[1],
        reverse=True
    )[:10]
    
    print("\nTop 10 PPR scorers for 2024:")
    for i, (name, pts, pos) in enumerate(top_scorers, 1):
        print(f"  {i}. {name} ({pos}): {pts:.1f} points")

def main():
    print("Loading stats files...")
    stats_data = load_stats_files()
    print(f"Loaded {len(stats_data)} stat entries")
    
    print("\nAggregating by player_id...")
    aggregated_data = aggregate_by_player(stats_data)
    
    print_summary(aggregated_data)
    
    print("\nSaving aggregated data...")
    save_aggregated_stats(aggregated_data, "aggregated_player_stats_2024.json")
    
    position_specific = defaultdict(dict)
    for player_id, player_data in aggregated_data.items():
        position = player_data['position']
        position_specific[position][player_id] = player_data
    
    for position, players in position_specific.items():
        if players:
            filename = f"aggregated_{position.lower()}_stats_2024.json"
            save_aggregated_stats(players, filename)
    
    print("\nAggregation complete!")

if __name__ == "__main__":
    main()