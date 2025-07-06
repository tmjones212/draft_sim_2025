#!/usr/bin/env python3
import json
import os
from typing import Dict, Any

# Import scoring configuration
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from src.config.scoring import SCORING_CONFIG

def calculate_week_fantasy_points(stats: Dict[str, Any]) -> float:
    """Calculate fantasy points for a single week based on custom scoring."""
    points = 0.0
    
    # Completions
    completions = stats.get('pass_cmp', 0)
    points += completions * SCORING_CONFIG['pass_completion']
    
    # Receptions
    receptions = stats.get('rec', 0)
    points += receptions * SCORING_CONFIG['reception']
    
    # Rushing yards
    rush_yards = stats.get('rush_yd', 0)
    points += rush_yards * SCORING_CONFIG['rush_yard']
    
    # Receiving yards
    rec_yards = stats.get('rec_yd', 0)
    points += rec_yards * SCORING_CONFIG['rec_yard']
    
    # Passing yards
    pass_yards = stats.get('pass_yd', 0)
    points += pass_yards * SCORING_CONFIG['pass_yard']
    
    # Touchdowns (all types)
    touchdowns = (
        stats.get('pass_td', 0) +
        stats.get('rush_td', 0) +
        stats.get('rec_td', 0)
    )
    points += touchdowns * SCORING_CONFIG['touchdown']
    
    # Bonuses
    if pass_yards >= 300:
        points += SCORING_CONFIG['bonus_pass_300_yards']
    
    if rush_yards >= 100:
        points += SCORING_CONFIG['bonus_rush_100_yards']
    
    if rec_yards >= 100:
        points += SCORING_CONFIG['bonus_rec_100_yards']
    
    return round(points, 2)

def recalculate_all_fantasy_points(input_file: str, output_file: str):
    """Recalculate fantasy points for all players using custom scoring."""
    
    # Load aggregated data
    with open(input_file, 'r') as f:
        players_data = json.load(f)
    
    # Recalculate points for each player
    for player_id, player in players_data.items():
        player['custom_season_total'] = 0.0
        player['custom_weekly_stats'] = []
        
        for week_stat in player.get('weekly_stats', []):
            week_points = calculate_week_fantasy_points(week_stat['stats'])
            
            custom_week = {
                'year': week_stat['year'],
                'week': week_stat['week'],
                'team': week_stat['team'],
                'opponent': week_stat['opponent'],
                'custom_points': week_points,
                'stats': week_stat['stats']
            }
            
            player['custom_weekly_stats'].append(custom_week)
            player['custom_season_total'] += week_points
        
        player['custom_season_total'] = round(player['custom_season_total'], 2)
        
        # Calculate average
        games_played = player.get('games_played', 0)
        if games_played > 0:
            player['custom_average'] = round(player['custom_season_total'] / games_played, 2)
        else:
            player['custom_average'] = 0.0
    
    # Save updated data
    with open(output_file, 'w') as f:
        json.dump(players_data, f, indent=2)
    
    return players_data

def print_top_scorers(players_data: Dict[str, Dict[str, Any]], position: str = None, top_n: int = 20):
    """Print top scorers by custom fantasy points."""
    
    # Filter by position if specified
    if position:
        filtered_players = [
            (p['player_name'], p['custom_season_total'], p['position'], p['games_played'])
            for p in players_data.values()
            if p['position'] == position
        ]
        title = f"Top {top_n} {position} Scorers (Custom Scoring)"
    else:
        filtered_players = [
            (p['player_name'], p['custom_season_total'], p['position'], p['games_played'])
            for p in players_data.values()
        ]
        title = f"Top {top_n} Overall Scorers (Custom Scoring)"
    
    # Sort by points
    top_scorers = sorted(filtered_players, key=lambda x: x[1], reverse=True)[:top_n]
    
    print(f"\n{title}:")
    print(f"{'Rank':<5} {'Player':<25} {'Pos':<4} {'Games':<6} {'Points':<8} {'PPG':<6}")
    print("-" * 60)
    
    for i, (name, points, pos, games) in enumerate(top_scorers, 1):
        ppg = round(points / games, 2) if games > 0 else 0
        print(f"{i:<5} {name:<25} {pos:<4} {games:<6} {points:<8.1f} {ppg:<6.1f}")

def main():
    print("Recalculating fantasy points with custom scoring...")
    print("\nScoring system:")
    print(f"  Completion: {SCORING_CONFIG['pass_completion']} pts")
    print(f"  Reception: {SCORING_CONFIG['reception']} pts")
    print(f"  Rush yard: {SCORING_CONFIG['rush_yard']} pts")
    print(f"  Rec yard: {SCORING_CONFIG['rec_yard']} pts")
    print(f"  Pass yard: {SCORING_CONFIG['pass_yard']} pts")
    print(f"  Any touchdown: {SCORING_CONFIG['touchdown']} pts")
    print(f"  300+ pass yards bonus: {SCORING_CONFIG['bonus_pass_300_yards']} pts")
    print(f"  100+ rush yards bonus: {SCORING_CONFIG['bonus_rush_100_yards']} pts")
    print(f"  100+ rec yards bonus: {SCORING_CONFIG['bonus_rec_100_yards']} pts")
    
    # Process all players
    input_file = os.path.join(os.path.dirname(__file__), "aggregated_player_stats_2024.json")
    output_file = os.path.join(os.path.dirname(__file__), "custom_scoring_player_stats_2024.json")
    
    players_data = recalculate_all_fantasy_points(input_file, output_file)
    print(f"\nProcessed {len(players_data)} players")
    print(f"Saved to: {output_file}")
    
    # Print top scorers
    print_top_scorers(players_data, None, 20)
    
    # Print top scorers by position
    for position in ['QB', 'RB', 'WR', 'TE']:
        print_top_scorers(players_data, position, 10)
    
    # Also create position-specific files with custom scoring
    positions = ['QB', 'RB', 'WR', 'TE']
    for position in positions:
        position_players = {
            pid: pdata for pid, pdata in players_data.items()
            if pdata['position'] == position
        }
        
        output_file = os.path.join(
            os.path.dirname(__file__),
            f"custom_scoring_{position.lower()}_stats_2024.json"
        )
        
        with open(output_file, 'w') as f:
            json.dump(position_players, f, indent=2)
        
        print(f"\nSaved {position} data to: {output_file}")

if __name__ == "__main__":
    main()