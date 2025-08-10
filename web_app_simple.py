#!/usr/bin/env python3
"""
Simple web server for mock draft - uses only Python standard library
No external dependencies required!
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import sys
import os
import urllib.parse
import socket

# Add the current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

import config
from src.models import Team, Player
from src.core import DraftEngine

# Import only what we need, avoiding PIL dependencies
def format_name(player):
    """Format player name for display"""
    if hasattr(player, 'name'):
        return player.name
    return str(player)

# Simple custom ADP manager
class SimpleCustomADPManager:
    def __init__(self):
        self.custom_adp_file = 'data/custom_adp.json'
    
    def load_custom_adp(self):
        try:
            with open(self.custom_adp_file, 'r') as f:
                return json.load(f)
        except:
            return {}

# Global draft state
draft_state = {
    'teams': {},
    'draft_engine': None,
    'all_players': [],
    'available_players': [],
    'draft_history': [],
    'custom_adp_manager': SimpleCustomADPManager()
}

def generate_simple_players():
    """Generate a simple list of players for the web app"""
    players_data = []
    
    # Try to load from local file first
    try:
        with open('src/data/players_2025.json', 'r') as f:
            data = json.load(f)
            for p in data.get('players', []):
                player = Player(
                    name=p['name'],
                    position=p['position'],
                    rank=p.get('rank', 999),
                    adp=p.get('adp', 999),
                    team=p.get('team', 'FA')
                )
                players_data.append(player)
    except:
        # Fallback to basic mock data
        mock_players = [
            ("Christian McCaffrey", "RB", "SF", 1),
            ("CeeDee Lamb", "WR", "DAL", 2),
            ("Breece Hall", "RB", "NYJ", 3),
            ("Bijan Robinson", "RB", "ATL", 4),
            ("Tyreek Hill", "WR", "MIA", 5),
            ("Ja'Marr Chase", "WR", "CIN", 6),
            ("Jonathan Taylor", "RB", "IND", 7),
            ("Saquon Barkley", "RB", "PHI", 8),
            ("Amon-Ra St. Brown", "WR", "DET", 9),
            ("Jahmyr Gibbs", "RB", "DET", 10),
            ("Justin Jefferson", "WR", "MIN", 11),
            ("A.J. Brown", "WR", "PHI", 12),
            ("Garrett Wilson", "WR", "NYJ", 13),
            ("Puka Nacua", "WR", "LAR", 14),
            ("De'Von Achane", "RB", "MIA", 15),
            ("Chris Olave", "WR", "NO", 16),
            ("Marvin Harrison Jr.", "WR", "ARI", 17),
            ("Davante Adams", "WR", "NYJ", 18),
            ("Mike Evans", "WR", "TB", 19),
            ("Derrick Henry", "RB", "BAL", 20),
            ("Joe Burrow", "QB", "CIN", 21),
            ("Josh Allen", "QB", "BUF", 22),
            ("Jalen Hurts", "QB", "PHI", 23),
            ("Lamar Jackson", "QB", "BAL", 24),
            ("Travis Kelce", "TE", "KC", 25),
        ]
        
        for name, pos, team, adp in mock_players:
            player = Player(
                name=name,
                position=pos,
                rank=adp,
                adp=adp,
                team=team
            )
            players_data.append(player)
    
    return players_data

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
    draft_state['all_players'] = generate_simple_players()
    
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

def get_draft_status():
    """Get current draft status"""
    if not draft_state['draft_engine']:
        return {'error': 'Draft not initialized'}
    
    pick_number, current_round, pick_in_round, team_on_clock = draft_state['draft_engine'].get_current_pick_info()
    
    return {
        'pick_number': pick_number,
        'round': current_round,
        'pick_in_round': pick_in_round,
        'team_on_clock': team_on_clock,
        'team_name': draft_state['teams'][team_on_clock].name if team_on_clock else '',
        'draft_complete': draft_state['draft_engine'].is_draft_complete(),
        'total_picks': draft_state['draft_engine'].total_picks
    }

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
                'adp': int(player.adp) if player.adp else 999
            })
    
    return available[:50]  # Return top 50 for performance

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
            if pick_number == 21:
                if team.can_draft_player(player):
                    return player
    
    # Regular draft logic - best available by ADP
    for player in available:
        if team.can_draft_player(player):
            return player
    
    return available[0] if available else None

def make_pick(player_id=None):
    """Make a draft pick"""
    if not draft_state['draft_engine']:
        return {'error': 'Draft not initialized'}
    
    _, _, _, team_on_clock = draft_state['draft_engine'].get_current_pick_info()
    
    if not team_on_clock:
        return {'error': 'Draft is complete'}
    
    # Find the player
    player = None
    if player_id:
        for p in draft_state['available_players']:
            if id(p) == player_id:
                player = p
                break
    
    if not player:
        player = make_computer_pick(team_on_clock)
        if not player:
            return {'error': 'No valid players available'}
    
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
    
    return {
        'status': 'success',
        'pick': {
            'pick_number': pick.pick_number,
            'team': team.name,
            'player_name': format_name(player),
            'position': player.position
        }
    }

def rollback_pick():
    """Roll back the last pick"""
    if not draft_state['draft_engine']:
        return {'error': 'Draft not initialized'}
    
    if not draft_state['draft_engine'].draft_results:
        return {'error': 'No picks to roll back'}
    
    # Remove last pick from engine
    last_pick = draft_state['draft_engine'].draft_results.pop()
    
    # Remove player from team
    team = draft_state['teams'][last_pick.team_id]
    team.roster = [p for p in team.roster if id(p) != id(last_pick.player)]
    
    # Remove from history
    if draft_state['draft_history']:
        draft_state['draft_history'].pop()
    
    return {'status': 'success'}

def get_draft_board():
    """Get the current draft board (first 5 rounds)"""
    board = []
    
    for round_num in range(1, min(6, sum(config.roster_spots.values()) + 1)):
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
                        'position': pick.player.position
                    }
                    break
            
            if not pick_data:
                # Empty pick slot
                team_id = draft_state['draft_engine'].draft_order[pick_number - 1]
                pick_data = {
                    'pick_number': pick_number,
                    'team': draft_state['teams'][team_id].name,
                    'player_name': '',
                    'position': ''
                }
            
            round_picks.append(pick_data)
        
        board.append({
            'round': round_num,
            'picks': round_picks
        })
    
    return board

# HTML content
HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Mock Draft 2025</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0e1117;
            color: #e1e3e8;
            padding: 10px;
        }
        .container { max-width: 100%; margin: 0 auto; }
        .header {
            background: #1a1d24;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 15px;
        }
        .status { font-size: 18px; font-weight: bold; margin-bottom: 5px; }
        .controls { display: flex; gap: 10px; margin-top: 10px; flex-wrap: wrap; }
        button {
            background: #3b82f6;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
        }
        button:active { transform: scale(0.98); }
        button.danger { background: #ef4444; }
        button.secondary { background: #6b7280; }
        .tabs {
            display: flex;
            gap: 5px;
            margin-bottom: 15px;
            border-bottom: 2px solid #1a1d24;
        }
        .tab {
            padding: 10px 20px;
            background: transparent;
            color: #9ca3af;
            border: none;
            border-bottom: 3px solid transparent;
            cursor: pointer;
            font-weight: 600;
        }
        .tab.active {
            color: #3b82f6;
            border-bottom-color: #3b82f6;
        }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .players-table {
            background: #1a1d24;
            border-radius: 8px;
            padding: 10px;
            max-height: 500px;
            overflow-y: auto;
        }
        .player-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px;
            border-bottom: 1px solid #2d3748;
            cursor: pointer;
        }
        .player-row:hover { background: #252a36; }
        .player-info { flex: 1; }
        .player-name { font-weight: 600; margin-bottom: 3px; }
        .player-details { font-size: 12px; color: #9ca3af; }
        .position-badge {
            display: inline-block;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 10px;
            font-weight: bold;
            margin-right: 5px;
        }
        .position-QB { background: #ec4899; color: white; }
        .position-RB { background: #14b8a6; color: white; }
        .position-WR { background: #3b82f6; color: white; }
        .position-TE { background: #f97316; color: white; }
        .draft-btn {
            background: #10b981;
            padding: 5px 15px;
            font-size: 12px;
        }
        .draft-board {
            background: #1a1d24;
            border-radius: 8px;
            padding: 10px;
        }
        .round { margin-bottom: 15px; }
        .round-header {
            font-weight: bold;
            color: #9ca3af;
            margin-bottom: 5px;
            font-size: 12px;
        }
        .picks {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
            gap: 5px;
        }
        .pick {
            background: #0e1117;
            padding: 8px;
            border-radius: 4px;
            font-size: 11px;
            border: 1px solid #2d3748;
        }
        .pick.current {
            border: 2px solid #3b82f6;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { border-color: #3b82f6; }
            50% { border-color: #60a5fa; }
        }
        .pick-number { color: #6b7280; font-size: 10px; }
        .pick-team { color: #9ca3af; font-weight: 600; margin: 2px 0; }
        .pick-player { color: #e1e3e8; font-weight: bold; }
        .loading { text-align: center; padding: 40px; color: #6b7280; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="status" id="draft-status">Loading...</div>
            <div style="font-size: 14px; color: #9ca3af;" id="on-clock"></div>
            <div class="controls">
                <button onclick="resetDraft()" class="danger">Reset</button>
                <button onclick="undoPick()" class="secondary">Undo</button>
                <button onclick="autoPick()">Auto Pick</button>
            </div>
        </div>

        <div class="tabs">
            <button class="tab active" onclick="showTab('players')">Players</button>
            <button class="tab" onclick="showTab('board')">Board</button>
        </div>

        <div id="players-tab" class="tab-content active">
            <div class="players-table" id="players-list">
                <div class="loading">Loading players...</div>
            </div>
        </div>

        <div id="board-tab" class="tab-content">
            <div class="draft-board" id="draft-board">
                <div class="loading">Loading draft board...</div>
            </div>
        </div>
    </div>

    <script>
        let currentPick = 0;

        function showTab(tab) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById(tab + '-tab').classList.add('active');
            if (tab === 'board') loadBoard();
        }

        async function api(endpoint, method = 'GET', data = null) {
            const options = { method };
            if (data) {
                options.headers = { 'Content-Type': 'application/json' };
                options.body = JSON.stringify(data);
            }
            const response = await fetch('/api/' + endpoint, options);
            return response.json();
        }

        async function loadStatus() {
            const data = await api('status');
            currentPick = data.pick_number;
            if (data.draft_complete) {
                document.getElementById('draft-status').textContent = 'Draft Complete!';
                document.getElementById('on-clock').textContent = '';
            } else {
                document.getElementById('draft-status').textContent = 
                    `Round ${data.round}, Pick ${data.pick_in_round} (Overall: ${data.pick_number})`;
                document.getElementById('on-clock').textContent = `On the clock: ${data.team_name}`;
            }
        }

        async function loadPlayers() {
            const players = await api('players');
            const list = document.getElementById('players-list');
            list.innerHTML = players.map(p => `
                <div class="player-row" onclick="draftPlayer(${p.id})">
                    <div class="player-info">
                        <div class="player-name">${p.name}</div>
                        <div class="player-details">
                            <span class="position-badge position-${p.position}">${p.position}</span>
                            ${p.team} • ADP: ${p.adp}
                        </div>
                    </div>
                    <button class="draft-btn" onclick="draftPlayer(${p.id}); event.stopPropagation();">Draft</button>
                </div>
            `).join('');
        }

        async function loadBoard() {
            const board = await api('board');
            const boardDiv = document.getElementById('draft-board');
            boardDiv.innerHTML = board.map(round => `
                <div class="round">
                    <div class="round-header">Round ${round.round}</div>
                    <div class="picks">
                        ${round.picks.map(pick => `
                            <div class="pick ${pick.pick_number === currentPick ? 'current' : ''}">
                                <div class="pick-number">Pick ${pick.pick_number}</div>
                                <div class="pick-team">${pick.team}</div>
                                ${pick.player_name ? `
                                    <div class="pick-player">
                                        ${pick.player_name}
                                        <span class="position-badge position-${pick.position}">${pick.position}</span>
                                    </div>
                                ` : ''}
                            </div>
                        `).join('')}
                    </div>
                </div>
            `).join('');
        }

        async function draftPlayer(playerId) {
            await api('pick', 'POST', { player_id: playerId });
            await refresh();
        }

        async function autoPick() {
            await api('pick', 'POST', {});
            await refresh();
        }

        async function undoPick() {
            await api('rollback', 'POST');
            await refresh();
        }

        async function resetDraft() {
            if (!confirm('Reset the entire draft?')) return;
            await api('init', 'POST');
            await refresh();
        }

        async function refresh() {
            await loadStatus();
            await loadPlayers();
            if (document.getElementById('board-tab').classList.contains('active')) {
                await loadBoard();
            }
        }

        // Initialize
        refresh();
        setInterval(loadStatus, 5000);
    </script>
</body>
</html>"""

class DraftHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode())
        elif self.path == '/api/status':
            self.send_json(get_draft_status())
        elif self.path == '/api/players':
            self.send_json(get_available_players())
        elif self.path == '/api/board':
            self.send_json(get_draft_board())
        else:
            self.send_error(404)
    
    def do_POST(self):
        """Handle POST requests"""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length else b'{}'
        data = json.loads(body)
        
        if self.path == '/api/init':
            initialize_draft()
            self.send_json({'status': 'success'})
        elif self.path == '/api/pick':
            player_id = data.get('player_id')
            result = make_pick(player_id)
            self.send_json(result)
        elif self.path == '/api/rollback':
            result = rollback_pick()
            self.send_json(result)
        else:
            self.send_error(404)
    
    def send_json(self, data):
        """Send JSON response"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def log_message(self, format, *args):
        """Suppress request logging"""
        pass

def main():
    # Initialize draft
    initialize_draft()
    
    # Get local IP
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    # Start server
    port = 8080
    server = HTTPServer(('0.0.0.0', port), DraftHandler)
    
    print(f"\n{'='*50}")
    print(f"Mock Draft Web Server Started!")
    print(f"{'='*50}")
    print(f"Access on this computer: http://localhost:{port}")
    print(f"Access on your phone: http://{local_ip}:{port}")
    print(f"{'='*50}")
    print(f"Press Ctrl+C to stop the server\n")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")

if __name__ == '__main__':
    main()