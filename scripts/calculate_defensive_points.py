#!/usr/bin/env python3
"""Calculate defensive player fantasy points for 2024 season"""

import json
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.scoring import SCORING_CONFIG

def calculate_defensive_points(stats):
    """Calculate defensive fantasy points"""
    points = 0.0
    
    # IDP stats use different field names
    solo_tackles = stats.get('idp_tkl_solo', 0)
    total_tackles = stats.get('idp_tkl', 0)
    assist_tackles = max(0, total_tackles - solo_tackles)
    
    points += solo_tackles * SCORING_CONFIG.get('tackle_solo', 1.75)
    points += assist_tackles * SCORING_CONFIG.get('tackle_assist', 1.0)
    points += stats.get('idp_sack', 0) * SCORING_CONFIG.get('sack', 4.0)
    points += stats.get('idp_int', 0) * SCORING_CONFIG.get('int', 6.0)
    points += stats.get('idp_ff', 0) * SCORING_CONFIG.get('ff', 4.0)
    points += stats.get('idp_fr', 0) * SCORING_CONFIG.get('fr', 3.0)
    points += stats.get('idp_def_td', 0) * SCORING_CONFIG.get('def_td', 6.0)
    points += stats.get('idp_safety', 0) * SCORING_CONFIG.get('safety', 2.0)
    points += stats.get('idp_pass_def', 0) * SCORING_CONFIG.get('pass_defended', 1.5)
    
    return points

def main():
    # Load aggregated stats
    with open('aggregated_player_stats_2024.json', 'r') as f:
        all_stats = json.load(f)
    
    # Calculate defensive points
    defensive_totals = {}
    
    for player_id, player_data in all_stats.items():
        position = player_data.get('position')
        if position not in ['LB', 'DB']:
            continue
            
        player_name = player_data.get('player_name', 'Unknown')
        weekly_stats = player_data.get('weekly_stats', [])
        
        total_points = 0
        games_played = 0
        
        for week_data in weekly_stats:
            stats = week_data.get('stats', {})
            # Only count games where they played
            if stats.get('def_snp', 0) > 0:
                week_points = calculate_defensive_points(stats)
                total_points += week_points
                games_played += 1
        
        defensive_totals[player_id] = {
            'player_name': player_name,
            'position': position,
            'games_played': games_played,
            'total_points': round(total_points, 1),
            'ppg': round(total_points / games_played, 1) if games_played > 0 else 0
        }
    
    # Sort by total points
    sorted_players = sorted(
        defensive_totals.items(), 
        key=lambda x: x[1]['total_points'], 
        reverse=True
    )
    
    # Print top 20
    print("\nTop 20 Defensive Players by 2024 Fantasy Points:")
    print(f"{'Rank':<5} {'Name':<25} {'Pos':<4} {'Games':<6} {'Points':<8} {'PPG':<6}")
    print("-" * 60)
    
    for i, (player_id, data) in enumerate(sorted_players[:20], 1):
        print(f"{i:<5} {data['player_name']:<25} {data['position']:<4} "
              f"{data['games_played']:<6} {data['total_points']:<8} {data['ppg']:<6}")
    
    # Save defensive points to file
    with open('defensive_player_points_2024.json', 'w') as f:
        json.dump(defensive_totals, f, indent=2)
    
    print(f"\nSaved {len(defensive_totals)} defensive player totals to defensive_player_points_2024.json")

if __name__ == '__main__':
    main()