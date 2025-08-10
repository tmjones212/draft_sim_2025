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
    this.userTeamId = null; // Will be set when user picks spot
    this.draftStarted = false;
    this.manualMode = true; // Default to manual mode
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
    this.loadState(); // Try to load saved state
    this.render();
  }
  
  selectDraftSpot(spotNumber) {
    this.userTeamId = spotNumber;
    this.draftStarted = true;
    this.saveState();
    this.render();
    
    // Only auto-pick if not in manual mode
    if (!this.manualMode && this.getCurrentTeam() !== this.userTeamId) {
      setTimeout(() => this.makeComputerPick(), 1000);
    }
  }
  
  toggleMode() {
    this.manualMode = !this.manualMode;
    this.saveState();
    this.render();
    
    // If switching to auto mode and it's computer's turn, start auto-picking
    if (!this.manualMode && this.getCurrentTeam() !== this.userTeamId) {
      setTimeout(() => this.makeComputerPick(), 1000);
    }
  }
  
  makeAutoPick() {
    // For manual mode - make one computer pick
    if (this.getCurrentTeam() !== this.userTeamId) {
      this.makeComputerPick();
    }
  }

  async loadPlayers() {
    try {
      const response = await fetch('web_static/players_data.json');
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
    // Don't allow picks if draft hasn't started
    if (!this.draftStarted || !this.userTeamId) {
      alert('Please select your draft spot first!');
      return false;
    }
    
    // Only allow user to pick on their turn
    if (this.getCurrentTeam() !== this.userTeamId) {
      return false;
    }
    
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
    
    // Auto-pick for computer teams only if not in manual mode
    if (!this.manualMode && this.currentPick <= this.totalPicks && this.getCurrentTeam() !== this.userTeamId) {
      setTimeout(() => this.makeComputerPick(), 1000);
    }
    
    this.render();
    return true;
  }

  makeComputerPick() {
    if (this.availablePlayers.length === 0 || this.currentPick > this.totalPicks) return;
    
    const teamId = this.getCurrentTeam();
    const team = this.teams[teamId];
    
    // Don't auto-pick for user
    if (teamId === this.userTeamId) return;
    
    let player = null;
    
    // Special rules
    if (this.currentPick <= 2) {
      player = this.availablePlayers.find(p => p.name.includes('CHASE') && p.position === 'WR');
    }
    
    if (!player && this.currentPick <= 21) {
      player = this.availablePlayers.find(p => p.name.includes('BURROW') && p.position === 'QB');
    }
    
    // Simple BPA with position needs
    if (!player) {
      const needPositions = this.getTeamNeeds(team);
      player = this.availablePlayers[0]; // Best available by ADP
      
      // Try to fill needs if we're past the early rounds
      if (this.currentPick > 30 && needPositions.length > 0) {
        const needPlayer = this.availablePlayers.find(p => needPositions.includes(p.position));
        if (needPlayer && this.availablePlayers.indexOf(needPlayer) < 10) {
          player = needPlayer;
        }
      }
    }
    
    if (!player) return;
    
    // Make the pick directly without calling makePick (to avoid recursion)
    team.roster.push(player);
    team.positionCounts[player.position] = (team.positionCounts[player.position] || 0) + 1;
    
    this.availablePlayers = this.availablePlayers.filter(p => p.id !== player.id);
    this.draftedPlayers.push({
      pick: this.currentPick,
      teamId: teamId,
      player: player
    });
    
    this.currentPick++;
    this.saveState();
    this.render();
    
    // Continue auto-picking for next computer team only if not in manual mode
    if (!this.manualMode && this.currentPick <= this.totalPicks && this.getCurrentTeam() !== this.userTeamId) {
      setTimeout(() => this.makeComputerPick(), 1000);
    }
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
    this.userTeamId = null;
    this.draftStarted = false;
    this.initializeTeams();
    localStorage.removeItem('draftState'); // Clear saved state
    this.render();
  }

  saveState() {
    const state = {
      currentPick: this.currentPick,
      draftedPlayers: this.draftedPlayers,
      teams: this.teams,
      userTeamId: this.userTeamId,
      draftStarted: this.draftStarted,
      manualMode: this.manualMode
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
      this.userTeamId = data.userTeamId;
      this.draftStarted = data.draftStarted;
      this.manualMode = data.manualMode !== undefined ? data.manualMode : true;
      
      // Rebuild available players
      const draftedIds = new Set(this.draftedPlayers.map(d => d.player.id));
      this.availablePlayers = this.allPlayers.filter(p => !draftedIds.has(p.id));
      
      // Resume auto-picking if needed (only if not in manual mode)
      if (!this.manualMode && this.draftStarted && this.getCurrentTeam() !== this.userTeamId) {
        setTimeout(() => this.makeComputerPick(), 1000);
      }
    }
  }

  render() {
    // Update status
    const statusEl = document.getElementById('draft-status');
    if (statusEl) {
      if (!this.draftStarted || !this.userTeamId) {
        // Show draft spot selection
        let spotsHtml = '<div style="padding: 10px;"><h3>Select Your Draft Position:</h3><div style="display: flex; gap: 10px; flex-wrap: wrap; justify-content: center; margin-top: 15px;">';
        for (let i = 1; i <= this.numTeams; i++) {
          spotsHtml += `<button onclick="draft.selectDraftSpot(${i})" style="width: 60px; height: 60px; font-size: 20px;">${i}</button>`;
        }
        spotsHtml += '</div></div>';
        statusEl.innerHTML = spotsHtml;
      } else {
        const currentTeam = this.getCurrentTeam();
        const isUserPick = currentTeam === this.userTeamId;
        statusEl.innerHTML = `
          <div style="padding: 10px; background: ${isUserPick ? '#2a4e2a' : '#1a1d23'}; border-radius: 5px;">
            <strong>Pick ${this.currentPick} / ${this.totalPicks}</strong> - 
            ${isUserPick ? 'YOUR PICK' : `Team ${currentTeam}'s Pick`}
            <br><small>You are Team ${this.userTeamId} | Mode: ${this.manualMode ? 'MANUAL' : 'AUTO'}</small>
            ${!isUserPick && this.manualMode ? '<br><button onclick="draft.makeAutoPick()" style="margin-top: 10px;">Make Computer Pick</button>' : ''}
          </div>
        `;
      }
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
    
    const isUserTurn = this.draftStarted && this.getCurrentTeam() === this.userTeamId;
    const cursorStyle = isUserTurn ? 'cursor: pointer;' : 'cursor: not-allowed; opacity: 0.7;';

    const html = this.availablePlayers.slice(0, 50).map(player => `
      <div class="player-row" onclick="draft.makePick('${player.id}')" style="${cursorStyle} padding: 8px; border-bottom: 1px solid #333; display: flex; justify-content: space-between; align-items: center;">
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
    navigator.serviceWorker.register('web_static/service-worker.js')
      .then(reg => console.log('Service Worker registered'))
      .catch(err => console.error('Service Worker registration failed:', err));
  }
});