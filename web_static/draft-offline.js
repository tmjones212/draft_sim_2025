// Offline-capable draft simulator
class DraftSimulator {
  constructor() {
    this.allPlayers = [];
    this.availablePlayers = [];
    this.draftedPlayers = [];
    this.teams = {};
    this.currentPick = 1;
    this.totalPicks = 0;
    this.numTeams = 10;
    this.userTeamId = 1;
    this.rosterSpots = {
      QB: 2,
      RB: 5,
      WR: 6,
      TE: 2,
      FLEX: 2,
      LB: 3,
      DB: 3
    };
    this.draftOrder = [];
    this.init();
  }

  async init() {
    await this.loadPlayers();
    this.initializeTeams();
    this.calculateDraftOrder();
    this.render();
  }

  async loadPlayers() {
    try {
      const response = await fetch('/web_static/players_data.json');
      const data = await response.json();
      this.allPlayers = data.players;
      this.availablePlayers = [...this.allPlayers];
      console.log(`Loaded ${this.allPlayers.length} players`);
    } catch (error) {
      console.error('Error loading players:', error);
      // Try to load from localStorage if offline
      const cached = localStorage.getItem('playersData');
      if (cached) {
        const data = JSON.parse(cached);
        this.allPlayers = data.players;
        this.availablePlayers = [...this.allPlayers];
        console.log(`Loaded ${this.allPlayers.length} players from cache`);
      }
    }
  }

  initializeTeams() {
    for (let i = 1; i <= this.numTeams; i++) {
      this.teams[i] = {
        id: i,
        name: i === this.userTeamId ? 'Your Team' : `Team ${i}`,
        roster: [],
        positionCounts: {}
      };
    }
    this.totalPicks = this.numTeams * Object.values(this.rosterSpots).reduce((a, b) => a + b, 0);
  }

  calculateDraftOrder() {
    const rounds = Math.ceil(this.totalPicks / this.numTeams);
    this.draftOrder = [];
    
    for (let round = 1; round <= rounds; round++) {
      const order = [];
      for (let i = 1; i <= this.numTeams; i++) {
        order.push(i);
      }
      
      // Snake draft with 3rd round reversal
      if (round % 2 === 0 && round !== 3) {
        order.reverse();
      } else if (round === 3 && rounds > 2) {
        // Round 3 goes same direction as round 2
        order.reverse();
      }
      
      this.draftOrder.push(...order);
    }
  }

  getCurrentTeam() {
    return this.draftOrder[this.currentPick - 1];
  }

  makePick(playerId) {
    const player = this.availablePlayers.find(p => p.id === playerId);
    if (!player) return false;

    const teamId = this.getCurrentTeam();
    const team = this.teams[teamId];
    
    // Add to team roster
    team.roster.push(player);
    team.positionCounts[player.position] = (team.positionCounts[player.position] || 0) + 1;
    
    // Remove from available
    this.availablePlayers = this.availablePlayers.filter(p => p.id !== playerId);
    this.draftedPlayers.push({
      pick: this.currentPick,
      teamId: teamId,
      player: player
    });
    
    this.currentPick++;
    
    // Save state to localStorage
    this.saveState();
    
    // Auto-pick for computer teams
    if (this.currentPick <= this.totalPicks && this.getCurrentTeam() !== this.userTeamId) {
      setTimeout(() => this.makeComputerPick(), 500);
    }
    
    this.render();
    return true;
  }

  makeComputerPick() {
    if (this.availablePlayers.length === 0) return;
    
    const teamId = this.getCurrentTeam();
    const team = this.teams[teamId];
    
    // Special rules
    if (this.currentPick <= 2) {
      const chase = this.availablePlayers.find(p => p.name.includes('CHASE') && p.position === 'WR');
      if (chase) {
        this.makePick(chase.id);
        return;
      }
    }
    
    if (this.currentPick <= 21) {
      const burrow = this.availablePlayers.find(p => p.name.includes('BURROW') && p.position === 'QB');
      if (burrow) {
        this.makePick(burrow.id);
        return;
      }
    }
    
    // Simple BPA with position needs
    const needPositions = this.getTeamNeeds(team);
    let pick = this.availablePlayers[0]; // Best available by ADP
    
    // Try to fill needs if we're past the early rounds
    if (this.currentPick > 30 && needPositions.length > 0) {
      const needPlayer = this.availablePlayers.find(p => needPositions.includes(p.position));
      if (needPlayer && this.availablePlayers.indexOf(needPlayer) < 10) {
        pick = needPlayer;
      }
    }
    
    this.makePick(pick.id);
  }

  getTeamNeeds(team) {
    const needs = [];
    const counts = team.positionCounts;
    
    if ((counts.QB || 0) < this.rosterSpots.QB) needs.push('QB');
    if ((counts.RB || 0) < this.rosterSpots.RB) needs.push('RB');
    if ((counts.WR || 0) < this.rosterSpots.WR) needs.push('WR');
    if ((counts.TE || 0) < this.rosterSpots.TE) needs.push('TE');
    if ((counts.LB || 0) < this.rosterSpots.LB && this.currentPick > 90) needs.push('LB');
    if ((counts.DB || 0) < this.rosterSpots.DB && this.currentPick > 90) needs.push('DB');
    
    return needs;
  }

  rollback() {
    if (this.draftedPlayers.length === 0) return;
    
    const lastPick = this.draftedPlayers.pop();
    const team = this.teams[lastPick.teamId];
    
    // Remove from team roster
    team.roster = team.roster.filter(p => p.id !== lastPick.player.id);
    team.positionCounts[lastPick.player.position]--;
    
    // Add back to available
    this.availablePlayers.push(lastPick.player);
    this.availablePlayers.sort((a, b) => a.adp - b.adp);
    
    this.currentPick--;
    this.saveState();
    this.render();
  }

  restart() {
    this.availablePlayers = [...this.allPlayers];
    this.draftedPlayers = [];
    this.currentPick = 1;
    this.initializeTeams();
    this.saveState();
    this.render();
  }

  saveState() {
    const state = {
      currentPick: this.currentPick,
      draftedPlayers: this.draftedPlayers,
      teams: this.teams
    };
    localStorage.setItem('draftState', JSON.stringify(state));
    localStorage.setItem('playersData', JSON.stringify({ players: this.allPlayers }));
  }

  loadState() {
    const state = localStorage.getItem('draftState');
    if (state) {
      const data = JSON.parse(state);
      this.currentPick = data.currentPick;
      this.draftedPlayers = data.draftedPlayers;
      this.teams = data.teams;
      
      // Rebuild available players
      const draftedIds = new Set(this.draftedPlayers.map(d => d.player.id));
      this.availablePlayers = this.allPlayers.filter(p => !draftedIds.has(p.id));
    }
  }

  render() {
    // Update status
    const statusEl = document.getElementById('draft-status');
    if (statusEl) {
      const currentTeam = this.getCurrentTeam();
      const isUserPick = currentTeam === this.userTeamId;
      statusEl.innerHTML = `
        <div style="padding: 10px; background: ${isUserPick ? '#2a4e2a' : '#1a1d23'}; border-radius: 5px;">
          <strong>Pick ${this.currentPick} / ${this.totalPicks}</strong> - 
          ${isUserPick ? 'YOUR PICK' : `Team ${currentTeam}'s Pick`}
        </div>
      `;
    }

    // Update available players
    this.renderAvailablePlayers();
    
    // Update draft board
    this.renderDraftBoard();
    
    // Update your team
    this.renderYourTeam();
  }

  renderAvailablePlayers() {
    const container = document.getElementById('available-players');
    if (!container) return;

    const positionColors = {
      QB: '#ff79c6',
      RB: '#50fa7b',
      WR: '#8be9fd',
      TE: '#ffb86c',
      LB: '#bd93f9',
      DB: '#f1fa8c'
    };

    const html = this.availablePlayers.slice(0, 50).map(player => `
      <div class="player-row" onclick="draft.makePick('${player.id}')" style="cursor: pointer; padding: 8px; border-bottom: 1px solid #333; display: flex; justify-content: space-between; align-items: center;">
        <div style="flex: 1;">
          <span style="color: ${positionColors[player.position] || '#fff'}; font-weight: bold; margin-right: 10px;">${player.position}</span>
          <span>${player.name}</span>
          <span style="color: #888; margin-left: 10px;">${player.team}</span>
        </div>
        <div>
          <span style="color: #888;">ADP: ${player.adp}</span>
          ${player.var ? `<span style="color: #50fa7b; margin-left: 10px;">VAR: ${player.var.toFixed(1)}</span>` : ''}
        </div>
      </div>
    `).join('');

    container.innerHTML = html;
  }

  renderDraftBoard() {
    const container = document.getElementById('draft-board');
    if (!container) return;

    const rounds = Math.ceil(this.totalPicks / this.numTeams);
    let html = '<table style="width: 100%; border-collapse: collapse;">';
    html += '<thead><tr><th>Round</th>';
    
    for (let i = 1; i <= this.numTeams; i++) {
      html += `<th style="padding: 5px; border: 1px solid #333;">Team ${i}</th>`;
    }
    html += '</tr></thead><tbody>';

    for (let round = 1; round <= Math.min(rounds, 5); round++) {
      html += `<tr><td style="padding: 5px; border: 1px solid #333; font-weight: bold;">R${round}</td>`;
      
      for (let team = 1; team <= this.numTeams; team++) {
        const pick = this.draftedPlayers.find(p => {
          const pickRound = Math.ceil(p.pick / this.numTeams);
          const pickTeam = this.draftOrder[p.pick - 1];
          return pickRound === round && pickTeam === team;
        });
        
        html += '<td style="padding: 5px; border: 1px solid #333; font-size: 12px;">';
        if (pick) {
          html += `${pick.player.position} ${pick.player.name.split(' ').pop()}`;
        }
        html += '</td>';
      }
      html += '</tr>';
    }
    html += '</tbody></table>';
    
    container.innerHTML = html;
  }

  renderYourTeam() {
    const container = document.getElementById('your-team');
    if (!container) return;

    const team = this.teams[this.userTeamId];
    const byPosition = {};
    
    team.roster.forEach(player => {
      if (!byPosition[player.position]) byPosition[player.position] = [];
      byPosition[player.position].push(player);
    });

    let html = '<h3>Your Roster</h3>';
    ['QB', 'RB', 'WR', 'TE', 'LB', 'DB'].forEach(pos => {
      if (byPosition[pos]) {
        html += `<div style="margin-bottom: 10px;"><strong>${pos}:</strong> `;
        html += byPosition[pos].map(p => p.name).join(', ');
        html += '</div>';
      }
    });

    container.innerHTML = html;
  }
}

// Initialize on page load
let draft;
document.addEventListener('DOMContentLoaded', () => {
  draft = new DraftSimulator();
  
  // Register service worker
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/web_static/service-worker.js')
      .then(reg => console.log('Service Worker registered'))
      .catch(err => console.error('Service Worker registration failed:', err));
  }
});