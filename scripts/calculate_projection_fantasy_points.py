#!/usr/bin/env python3
import json
import os
from typing import Dict, Any
from datetime import datetime

# Import scoring configuration
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from src.config.scoring import SCORING_CONFIG

def calculate_week_fantasy_points(projections: Dict[str, Any]) -> float:
    """Calculate fantasy points for a single week based on custom scoring."""
    points = 0.0
    
    # Completions
    completions = projections.get('pass_cmp', 0)
    points += completions * SCORING_CONFIG['pass_completion']
    
    # Receptions
    receptions = projections.get('rec', 0)
    points += receptions * SCORING_CONFIG['reception']
    
    # Rushing yards
    rush_yards = projections.get('rush_yd', 0)
    points += rush_yards * SCORING_CONFIG['rush_yard']
    
    # Receiving yards
    rec_yards = projections.get('rec_yd', 0)
    points += rec_yards * SCORING_CONFIG['rec_yard']
    
    # Passing yards
    pass_yards = projections.get('pass_yd', 0)
    points += pass_yards * SCORING_CONFIG['pass_yard']
    
    # Touchdowns (all types)
    touchdowns = (
        projections.get('pass_td', 0) +
        projections.get('rush_td', 0) +
        projections.get('rec_td', 0)
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

def recalculate_all_projection_points(year: int):
    """Recalculate fantasy points for all player projections using custom scoring."""
    
    input_file = os.path.join(os.path.dirname(__file__), f"aggregated_player_projections_{year}.json")
    output_file = os.path.join(os.path.dirname(__file__), f"custom_scoring_player_projections_{year}.json")
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found. Run aggregate_projections.py first.")
        return None
    
    # Load aggregated projection data
    with open(input_file, 'r') as f:
        players_data = json.load(f)
    
    # Recalculate points for each player
    for player_id, player in players_data.items():
        player['custom_projection_total'] = 0.0
        player['custom_weekly_projections'] = []
        
        for week_proj in player.get('weekly_projections', []):
            week_points = calculate_week_fantasy_points(week_proj['projections'])
            
            custom_week = {
                'year': week_proj['year'],
                'week': week_proj['week'],
                'team': week_proj['team'],
                'opponent': week_proj['opponent'],
                'custom_points': week_points,
                'projections': week_proj['projections']
            }
            
            player['custom_weekly_projections'].append(custom_week)
            player['custom_projection_total'] += week_points
        
        player['custom_projection_total'] = round(player['custom_projection_total'], 2)
        
        # Calculate average per game
        weeks_projected = player.get('weeks_projected', 0)
        if weeks_projected > 0:
            player['custom_projection_average'] = round(player['custom_projection_total'] / weeks_projected, 2)
        else:
            player['custom_projection_average'] = 0.0
    
    # Save updated data
    with open(output_file, 'w') as f:
        json.dump(players_data, f, indent=2)
    
    return players_data, output_file

def print_top_projected_scorers(players_data: Dict[str, Dict[str, Any]], year: int, position: str = None, top_n: int = 20):
    """Print top projected scorers by custom fantasy points."""
    
    # Filter by position if specified
    if position:
        filtered_players = [
            (p['player_name'], p['custom_projection_total'], p['position'], p['weeks_projected'])
            for p in players_data.values()
            if p['position'] == position
        ]
        title = f"Top {top_n} Projected {position} Scorers for {year} (Custom Scoring)"
    else:
        filtered_players = [
            (p['player_name'], p['custom_projection_total'], p['position'], p['weeks_projected'])
            for p in players_data.values()
        ]
        title = f"Top {top_n} Overall Projected Scorers for {year} (Custom Scoring)"
    
    # Sort by points
    top_scorers = sorted(filtered_players, key=lambda x: x[1], reverse=True)[:top_n]
    
    print(f"\n{title}:")
    print(f"{'Rank':<5} {'Player':<25} {'Pos':<4} {'Weeks':<6} {'Points':<8} {'PPG':<6}")
    print("-" * 60)
    
    for i, (name, points, pos, weeks) in enumerate(top_scorers, 1):
        ppg = round(points / weeks, 2) if weeks > 0 else 0
        print(f"{i:<5} {name:<25} {pos:<4} {weeks:<6} {points:<8.1f} {ppg:<6.1f}")

def main():
    # Determine projection year
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    if current_month < 9:
        projection_year = current_year
    else:
        projection_year = current_year + 1
    
    print(f"Recalculating {projection_year} projection fantasy points with custom scoring...")
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
    
    # Process all player projections
    result = recalculate_all_projection_points(projection_year)
    if not result:
        return
    
    players_data, output_file = result
    print(f"\nProcessed {len(players_data)} players")
    print(f"Saved to: {output_file}")
    
    # Print top projected scorers
    print_top_projected_scorers(players_data, projection_year, None, 20)
    
    # Print top projected scorers by position
    for position in ['QB', 'RB', 'WR', 'TE']:
        print_top_projected_scorers(players_data, projection_year, position, 10)
    
    # Also create position-specific files with custom scoring
    positions = ['QB', 'RB', 'WR', 'TE']
    for position in positions:
        position_players = {
            pid: pdata for pid, pdata in players_data.items()
            if pdata['position'] == position
        }
        
        output_file = os.path.join(
            os.path.dirname(__file__),
            f"custom_scoring_{position.lower()}_projections_{projection_year}.json"
        )
        
        with open(output_file, 'w') as f:
            json.dump(position_players, f, indent=2)
        
        print(f"\nSaved {position} projection data to: {output_file}")

if __name__ == "__main__":
    main()