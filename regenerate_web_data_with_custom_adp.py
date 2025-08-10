#!/usr/bin/env python3
"""Regenerate web players data with custom ADP values applied"""

import json
import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(__file__))

def main():
    # Import after path is set
    from src.utils.player_data_fetcher import get_players_with_fallback
    from src.utils.player_extensions import format_name
    from src.services.custom_adp_manager import CustomADPManager
    from src.utils.player_generator import generate_mock_players
    
    # Generate players
    print("Generating players...")
    players = generate_mock_players()
    
    # Load and apply custom ADP
    print("Applying custom ADP values...")
    adp_manager = CustomADPManager()
    adp_manager.apply_custom_adp_to_players(players)
    
    # Sort by ADP
    players.sort(key=lambda x: x.adp if x.adp else 999)
    
    # Find and print Derrick Henry's ADP
    for p in players:
        if 'HENRY' in p.name and p.position == 'RB':
            print(f"Derrick Henry: ADP = {p.adp}")
            break
    
    # Convert to JSON format
    players_data = []
    for player in players:
        player_dict = {
            'id': str(player.player_id) if player.player_id else str(hash(player.name)),
            'name': player.name,
            'position': player.position,
            'team': player.team or '',
            'adp': float(player.adp) if player.adp else 999.0,
            'rank': player.rank,
            'projection': float(player.points_2025_proj) if player.points_2025_proj else 0.0,
            'bye_week': player.bye_week or 0,
            'var': float(player.var) if player.var else 0.0,
            'points_2024': float(player.points_2024) if player.points_2024 else 0.0
        }
        players_data.append(player_dict)
    
    # Add kickers if not present
    k_count = sum(1 for p in players_data if p['position'] == 'K')
    if k_count == 0:
        kickers = [
            ('JAKE BATES', 'DET', 151),
            ('CAMERON DICKER', 'LAC', 152),
            ('BRANDON AUBREY', 'DAL', 153),
            ('CHRIS BOSWELL', 'PIT', 154),
            ('JUSTIN TUCKER', 'BAL', 155),
            ('TYLER BASS', 'BUF', 156),
            ('KAIMI FAIRBAIRN', 'HOU', 157),
            ('YOUNGHOE KOO', 'ATL', 158),
            ('JAKE ELLIOTT', 'PHI', 159),
            ('HARRISON BUTKER', 'KC', 160),
            ('JASON SANDERS', 'MIA', 161),
            ('EVAN MCPHERSON', 'CIN', 162),
            ('BLAKE GRUPE', 'NO', 163),
            ('WILL REICHARD', 'MIN', 164),
            ('CAMERON LITTLE', 'JAX', 165),
            ('JASON MYERS', 'SEA', 166),
            ('GREG ZUERLEIN', 'NYJ', 167),
            ('NICK FOLK', 'TEN', 168),
            ('CAIRO SANTOS', 'CHI', 169),
            ('MATT GAY', 'IND', 170)
        ]
        for name, team, adp in kickers:
            players_data.append({
                'id': str(hash(name)),
                'name': name,
                'position': 'K',
                'team': team,
                'adp': float(adp),
                'rank': adp,
                'projection': 0.0,
                'bye_week': 0,
                'var': 0.0,
                'points_2024': 0.0
            })
    
    # Add DSTs if not present
    dst_count = sum(1 for p in players_data if p['position'] == 'DST')
    if dst_count == 0:
        dst_teams = [
            ('TEXANS D/ST', 'HOU', 171),
            ('RAVENS D/ST', 'BAL', 172),
            ('BRONCOS D/ST', 'DEN', 173),
            ('EAGLES D/ST', 'PHI', 174),
            ('VIKINGS D/ST', 'MIN', 175),
            ('STEELERS D/ST', 'PIT', 176),
            ('PATRIOTS D/ST', 'NE', 177),
            ('PACKERS D/ST', 'GB', 178),
            ('LIONS D/ST', 'DET', 179),
            ('SEAHAWKS D/ST', 'SEA', 180),
            ('JETS D/ST', 'NYJ', 181),
            ('BILLS D/ST', 'BUF', 182),
            ('CHIEFS D/ST', 'KC', 183),
            ('DOLPHINS D/ST', 'MIA', 184),
            ('BUCCANEERS D/ST', 'TB', 185),
            ('CHARGERS D/ST', 'LAC', 186),
            ('CARDINALS D/ST', 'ARI', 187),
            ('COLTS D/ST', 'IND', 188),
            ('49ERS D/ST', 'SF', 189),
            ('RAMS D/ST', 'LAR', 190)
        ]
        for name, team, adp in dst_teams:
            players_data.append({
                'id': str(hash(name)),
                'name': name,
                'position': 'DST',
                'team': team,
                'adp': float(adp),
                'rank': adp,
                'projection': 0.0,
                'bye_week': 0,
                'var': 0.0,
                'points_2024': 0.0
            })
    
    # Sort by ADP
    players_data.sort(key=lambda x: x['adp'])
    
    # Save to JSON
    output = {'players': players_data}
    with open('web_static/players_data.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"Generated web_static/players_data.json with {len(players_data)} players")
    
    # Show top 30 for verification
    print("\nTop 30 players by ADP (with custom values):")
    for i, p in enumerate(players_data[:30], 1):
        print(f"{i:2}. {p['name']:25} ({p['position']:3}) ADP: {p['adp']:5.1f}")

if __name__ == '__main__':
    main()