from typing import List
from ..models import Player
from .player_data_fetcher import get_players_with_fallback
from .player_extensions import format_name


def calculate_position_ranks(players: List[Player]):
    """Calculate position ranks based on 2024 stats and projections"""
    # Group players by position
    position_groups = {'QB': [], 'RB': [], 'WR': [], 'TE': [], 'LB': [], 'DB': []}
    
    for player in players:
        if player.position in position_groups:
            position_groups[player.position].append(player)
    
    # Calculate 2024 position ranks (sort by points_2024, handle None values)
    for position, group in position_groups.items():
        # Sort by points_2024 (descending), putting None values at the end
        sorted_2024 = sorted(group, 
                           key=lambda p: (p.points_2024 is None, -(p.points_2024 or 0)))
        
        for rank, player in enumerate(sorted_2024, 1):
            if player.points_2024 is not None:
                player.position_rank_2024 = rank
    
    # Calculate projected position ranks (sort by points_2025_proj)
    for position, group in position_groups.items():
        # Sort by points_2025_proj (descending), putting None values at the end
        sorted_proj = sorted(group,
                           key=lambda p: (p.points_2025_proj is None, -(p.points_2025_proj or 0)))
        
        for rank, player in enumerate(sorted_proj, 1):
            if player.points_2025_proj is not None:
                player.position_rank_proj = rank


def calculate_var(players: List[Player], num_teams: int = 10):
    """Calculate Value Above Replacement for each player"""
    # Define replacement level for each position in a 10-team league
    replacement_levels = {
        'QB': 20,    # 2 QBs per team = 20th QB
        'RB': 22,    # 2.2 RBs per team (with flex) = 22nd RB
        'WR': 38,    # 3.8 WRs per team (with flex) = 38th WR
        'TE': 10,    # 1 TE per team = 10th TE
        'LB': 30,    # 3 LBs per team = 30th LB
        'DB': 30     # 3 DBs per team = 30th DB
    }
    
    # Group players by position
    position_groups = {'QB': [], 'RB': [], 'WR': [], 'TE': [], 'LB': [], 'DB': []}
    
    for player in players:
        if player.position in position_groups and player.points_2025_proj is not None:
            position_groups[player.position].append(player)
    
    # Calculate VAR for each position
    for position, group in position_groups.items():
        # Sort by projected points (descending)
        sorted_players = sorted(group, key=lambda p: p.points_2025_proj or 0, reverse=True)
        
        # Find replacement level points
        replacement_rank = replacement_levels.get(position, 10)
        replacement_points = 0
        
        if len(sorted_players) >= replacement_rank:
            replacement_points = sorted_players[replacement_rank - 1].points_2025_proj or 0
        elif sorted_players:
            # If we don't have enough players, use the last one
            replacement_points = sorted_players[-1].points_2025_proj or 0
        
        # Calculate VAR for each player
        for player in group:
            if player.points_2025_proj is not None:
                player.var = player.points_2025_proj - replacement_points


def generate_mock_players() -> List[Player]:
    """Generate players using real ADP data"""
    # Get real player data
    player_data = get_players_with_fallback()
    
    # Debug: Count positions in raw data
    position_counts = {}
    for p in player_data:
        pos = p.get('position', 'UNKNOWN')
        position_counts[pos] = position_counts.get(pos, 0) + 1
    print(f"DEBUG: Position counts in raw player_data: {position_counts}")
    
    players = []
    for data in player_data:
        player = Player(
            name=format_name(data['name']),
            position=data['position'],
            rank=data['rank'],
            adp=data['adp'],
            team=data.get('team'),
            player_id=data.get('player_id'),
            games_2024=data.get('games_2024'),
            points_2024=data.get('points_2024'),
            points_2025_proj=data.get('points_2025_proj'),
            weekly_stats_2024=data.get('weekly_stats_2024')
        )
        players.append(player)
    
    # Calculate position ranks
    calculate_position_ranks(players)
    
    # Calculate VAR (Value Above Replacement)
    calculate_var(players)
    
    # Only add fake players if we have very few real players (fallback scenario)
    if len(players) < 50:
        # If we don't have enough players, add some generic ones
        # to ensure draft can complete
        positions = ['QB', 'RB', 'WR', 'TE', 'LB', 'DB']
        pos_counts = {'QB': 0, 'RB': 0, 'WR': 0, 'TE': 0, 'LB': 0, 'DB': 0}
        
        for player in players:
            if player.position in pos_counts:
                pos_counts[player.position] += 1
        
        # Ensure minimum counts for a full draft
        min_needed = {
            'QB': 30,  # 3 per team
            'RB': 60,  # 6 per team
            'WR': 80,  # 8 per team
            'TE': 30,  # 3 per team
            'LB': 50,  # 5 per team
            'DB': 50   # 5 per team
        }
        
        current_rank = len(players) + 1
        
        for pos, min_count in min_needed.items():
            while pos_counts[pos] < min_count:
                player = Player(
                    name=f"{pos} Player {pos_counts[pos] + 1}",
                    position=pos,
                    rank=current_rank,
                    adp=current_rank,
                    team='FA'
                )
                players.append(player)
                pos_counts[pos] += 1
                current_rank += 1
    
    return players


def generate_fallback_players() -> List[Player]:
    """Generate basic mock players as fallback"""
    players = []
    
    # Position distribution for a typical fantasy league
    player_distribution = {
        "QB": 40,
        "RB": 80,
        "WR": 100,
        "TE": 40
    }
    
    rank = 1
    for position, count in player_distribution.items():
        for i in range(1, count + 1):
            player = Player(
                name=f"{position} Player {i}",
                position=position,
                rank=rank,
                adp=rank
            )
            players.append(player)
            rank += 1
    
    return players