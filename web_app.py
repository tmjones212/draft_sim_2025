#!/usr/bin/env python3
from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
import sys
import os
import json
import random

# Add the current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

import config
from src.models import Team, Player
from src.core import DraftEngine, DraftPick
from src.utils import generate_mock_players
from src.utils.player_extensions import format_name
from src.services.custom_adp_manager import CustomADPManager

app = Flask(__name__, static_folder='web_static', template_folder='web_templates')
CORS(app)

# Global state for the draft
draft_state = {
    'teams': {},
    'draft_engine': None,
    'all_players': [],
    'available_players': [],
    'draft_history': [],  # Store all picks for rollback
    'user_team_id': 1,
    'manual_mode': True,
    'custom_adp_manager': CustomADPManager()
}

def initialize_draft():
    """Initialize or reset the draft"""
    # Create teams
    draft_state['teams'] = {}
    for i in range(1, config.num_teams + 1):
        draft_state['teams'][i] = Team(
            team_id=i,
            name=f"Team {i}",
            roster_spots=config.roster_spots
        )
    
    # Create draft engine
    draft_state['draft_engine'] = DraftEngine(
        num_teams=config.num_teams,
        roster_spots=config.roster_spots,
        draft_type=config.draft_type,
        reversal_round=config.reversal_round
    )
    
    # Load players
    draft_state['all_players'] = generate_mock_players()
    
    # Apply custom ADP values
    custom_adp = draft_state['custom_adp_manager'].load_custom_adp()
    for player in draft_state['all_players']:
        player_key = f"{player.name}_{player.team}"
        if player_key in custom_adp:
            player.adp = custom_adp[player_key]
    
    # Sort by ADP
    draft_state['available_players'] = sorted(
        draft_state['all_players'],
        key=lambda p: p.adp if p.adp else 999
    )
    
    draft_state['draft_history'] = []

def get_draft_board():
    """Get the current draft board"""
    board = []
    total_rounds = sum(config.roster_spots.values())
    
    for round_num in range(1, total_rounds + 1):
        round_picks = []
        for pick_in_round in range(1, config.num_teams + 1):
            pick_number = (round_num - 1) * config.num_teams + pick_in_round
            
            # Find the pick in draft results
            pick_data = None
            for pick in draft_state['draft_engine'].draft_results:
                if pick.pick_number == pick_number:
                    pick_data = {
                        'pick_number': pick.pick_number,
                        'team': draft_state['teams'][pick.team_id].name,
                        'player_name': format_name(pick.player),
                        'position': pick.player.position,
                        'player_team': pick.player.team
                    }
                    break
            
            if not pick_data:
                # Empty pick slot
                team_id = draft_state['draft_engine'].draft_order[pick_number - 1]
                pick_data = {
                    'pick_number': pick_number,
                    'team': draft_state['teams'][team_id].name,
                    'player_name': '',
                    'position': '',
                    'player_team': ''
                }
            
            round_picks.append(pick_data)
        
        board.append({
            'round': round_num,
            'picks': round_picks
        })
    
    return board

def get_available_players():
    """Get list of available players"""
    drafted_player_ids = set()
    for pick in draft_state['draft_engine'].draft_results:
        drafted_player_ids.add(id(pick.player))
    
    available = []
    for player in draft_state['available_players']:
        if id(player) not in drafted_player_ids:
            available.append({
                'id': id(player),
                'name': format_name(player),
                'position': player.position,
                'team': player.team,
                'adp': player.adp if player.adp else 999,
                'projection': player.projection if hasattr(player, 'projection') else 0,
                'bye_week': player.bye_week if hasattr(player, 'bye_week') else 0
            })
    
    return available

def make_computer_pick(team_id):
    """Make a computer-controlled pick"""
    available = [p for p in draft_state['available_players'] 
                 if id(p) not in {id(pick.player) for pick in draft_state['draft_engine'].draft_results}]
    
    if not available:
        return None
    
    team = draft_state['teams'][team_id]
    pick_number = len(draft_state['draft_engine'].draft_results) + 1
    
    # Special player rules
    for player in available:
        if player.name == "Ja'Marr Chase" and pick_number <= 2:
            if team.can_draft_player(player):
                return player
        if player.name == "Joe Burrow" and pick_number <= 21:
            if pick_number == 21 or (pick_number >= 19 and random.random() < 0.3):
                if team.can_draft_player(player):
                    return player
    
    # Regular draft logic - best available by ADP
    for player in available:
        if team.can_draft_player(player):
            return player
    
    return available[0] if available else None

@app.route('/')
def index():
    """Serve the main draft page"""
    return render_template('draft.html')

@app.route('/api/init', methods=['POST'])
def init_draft():
    """Initialize or reset the draft"""
    initialize_draft()
    return jsonify({'status': 'success'})

@app.route('/api/status')
def get_status():
    """Get current draft status"""
    if not draft_state['draft_engine']:
        return jsonify({'error': 'Draft not initialized'}), 400
    
    pick_number, current_round, pick_in_round, team_on_clock = draft_state['draft_engine'].get_current_pick_info()
    
    return jsonify({
        'pick_number': pick_number,
        'round': current_round,
        'pick_in_round': pick_in_round,
        'team_on_clock': team_on_clock,
        'team_name': draft_state['teams'][team_on_clock].name if team_on_clock else '',
        'draft_complete': draft_state['draft_engine'].is_draft_complete(),
        'total_picks': draft_state['draft_engine'].total_picks,
        'manual_mode': draft_state['manual_mode'],
        'user_team_id': draft_state['user_team_id']
    })

@app.route('/api/draft_board')
def get_board():
    """Get the current draft board"""
    if not draft_state['draft_engine']:
        return jsonify({'error': 'Draft not initialized'}), 400
    
    return jsonify(get_draft_board())

@app.route('/api/available_players')
def get_available():
    """Get available players"""
    if not draft_state['draft_engine']:
        return jsonify({'error': 'Draft not initialized'}), 400
    
    return jsonify(get_available_players())

@app.route('/api/make_pick', methods=['POST'])
def make_pick():
    """Make a draft pick"""
    if not draft_state['draft_engine']:
        return jsonify({'error': 'Draft not initialized'}), 400
    
    data = request.json
    player_id = data.get('player_id')
    
    # Get current team on clock
    _, _, _, team_on_clock = draft_state['draft_engine'].get_current_pick_info()
    
    if not team_on_clock:
        return jsonify({'error': 'Draft is complete'}), 400
    
    # Find the player
    player = None
    for p in draft_state['available_players']:
        if id(p) == player_id:
            player = p
            break
    
    if not player:
        # If no player specified, make computer pick
        player = make_computer_pick(team_on_clock)
        if not player:
            return jsonify({'error': 'No valid players available'}), 400
    
    # Make the pick
    team = draft_state['teams'][team_on_clock]
    
    # Save state for rollback
    draft_state['draft_history'].append({
        'pick': len(draft_state['draft_engine'].draft_results),
        'team_id': team_on_clock,
        'player': player
    })
    
    # Execute pick
    pick = draft_state['draft_engine'].make_pick(team, player)
    
    return jsonify({
        'status': 'success',
        'pick': {
            'pick_number': pick.pick_number,
            'team': team.name,
            'player_name': format_name(player),
            'position': player.position
        }
    })

@app.route('/api/auto_pick', methods=['POST'])
def auto_pick():
    """Make an automatic computer pick"""
    if not draft_state['draft_engine']:
        return jsonify({'error': 'Draft not initialized'}), 400
    
    _, _, _, team_on_clock = draft_state['draft_engine'].get_current_pick_info()
    
    if not team_on_clock:
        return jsonify({'error': 'Draft is complete'}), 400
    
    player = make_computer_pick(team_on_clock)
    if not player:
        return jsonify({'error': 'No valid players available'}), 400
    
    # Make the pick
    team = draft_state['teams'][team_on_clock]
    
    # Save state for rollback
    draft_state['draft_history'].append({
        'pick': len(draft_state['draft_engine'].draft_results),
        'team_id': team_on_clock,
        'player': player
    })
    
    pick = draft_state['draft_engine'].make_pick(team, player)
    
    return jsonify({
        'status': 'success',
        'pick': {
            'pick_number': pick.pick_number,
            'team': team.name,
            'player_name': format_name(player),
            'position': player.position
        }
    })

@app.route('/api/rollback', methods=['POST'])
def rollback_pick():
    """Roll back the last pick"""
    if not draft_state['draft_engine']:
        return jsonify({'error': 'Draft not initialized'}), 400
    
    if not draft_state['draft_engine'].draft_results:
        return jsonify({'error': 'No picks to roll back'}), 400
    
    # Remove last pick from engine
    last_pick = draft_state['draft_engine'].draft_results.pop()
    
    # Remove player from team
    team = draft_state['teams'][last_pick.team_id]
    team.roster = [p for p in team.roster if id(p) != id(last_pick.player)]
    
    # Remove from history
    if draft_state['draft_history']:
        draft_state['draft_history'].pop()
    
    return jsonify({'status': 'success'})

@app.route('/api/set_mode', methods=['POST'])
def set_mode():
    """Set draft mode (manual or auto)"""
    data = request.json
    draft_state['manual_mode'] = data.get('manual_mode', True)
    draft_state['user_team_id'] = data.get('user_team_id', 1)
    
    return jsonify({'status': 'success'})

@app.route('/api/teams')
def get_teams():
    """Get all teams and their rosters"""
    teams = []
    for team_id, team in draft_state['teams'].items():
        roster = []
        for player in team.roster:
            roster.append({
                'name': format_name(player),
                'position': player.position,
                'team': player.team
            })
        teams.append({
            'id': team_id,
            'name': team.name,
            'roster': roster
        })
    
    return jsonify(teams)

# Serve static files
@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('web_static', path)

if __name__ == '__main__':
    # Initialize draft on startup
    initialize_draft()
    
    # Get local IP for mobile access
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    print(f"\n{'='*50}")
    print(f"Mock Draft Web Server Started!")
    print(f"{'='*50}")
    print(f"Access on this computer: http://localhost:5000")
    print(f"Access on your phone: http://{local_ip}:5000")
    print(f"{'='*50}\n")
    
    # Run server accessible from network
    app.run(host='0.0.0.0', port=5000, debug=True)