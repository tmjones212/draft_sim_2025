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
    this.positionFilter = 'ALL'; // Position filter
    this.sortBy = 'adp'; // Sort by 'adp' or 'var'
    this.adminMode = false; // Admin mode for custom ADP
    this.customPlayersData = null; // Store custom ADP data
    this.publicPlayersData = null; // Store public ADP data
    this.rosterSpots = {
      QB: 2,
      RB: 5,
      WR: 6,
      TE: 2,
      FLEX: 2,
      LB: 3,
      DB: 3,
      K: 1,
      DST: 1
    };
    this.draftOrder = [];
    this.init();
  }
  
  // VAR calculation is no longer needed - values come from JSON data which uses proper projected points

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
    
    // Only auto-pick if in auto mode AND it's not user's turn
    if (!this.manualMode && this.getCurrentTeam() !== this.userTeamId) {
      setTimeout(() => this.makeComputerPick(), 1000);
    }
  }
  
  toggleMode() {
    this.manualMode = !this.manualMode;
    console.log('Mode toggled to:', this.manualMode ? 'Manual' : 'Auto');
    this.saveState();
    this.render();
    
    // If switching to auto mode and it's computer's turn, start auto-picking
    if (!this.manualMode && this.draftStarted && this.getCurrentTeam() !== this.userTeamId) {
      console.log('Starting auto-pick for computer team');
      setTimeout(() => this.makeComputerPick(), 1000);
    }
  }
  
  setPositionFilter(position) {
    this.positionFilter = position;
    this.saveState();
    this.render();
  }
  
  setSortBy(sortType) {
    // Only allow VAR and NFC sort in admin mode
    if ((sortType === 'var' || sortType === 'nfc') && !this.adminMode) {
      return;
    }
    
    this.sortBy = sortType;
    // Sort available players
    if (sortType === 'adp') {
      this.availablePlayers.sort((a, b) => (a.adp || 999) - (b.adp || 999));
    } else if (sortType === 'var') {
      this.availablePlayers.sort((a, b) => {
        // Sort by VAR descending (higher VAR is better)
        const varA = parseFloat(a.var) || -999;
        const varB = parseFloat(b.var) || -999;
        return varB - varA;
      });
    } else if (sortType === 'nfc') {
      this.availablePlayers.sort((a, b) => (a.nfc_adp || 999) - (b.nfc_adp || 999));
    }
    this.saveState();
    this.render();
  }
  
  makeAutoPick() {
    // For manual mode - make one computer pick without triggering chain
    if (this.getCurrentTeam() !== this.userTeamId) {
      const savedMode = this.manualMode;
      this.manualMode = true; // Temporarily set to manual to prevent chain
      this.makeComputerPick();
      this.manualMode = savedMode; // Restore original mode
    }
  }

  formatName(name) {
    // Match the format_name function from Python
    name = name.split('(')[0];
    name = name.trim().toUpperCase();
    name = name.replace(/[,+.*]/g, '');
    name = name.replace(/\s+(JR|SR|III|II|IV|V)/g, '');
    name = name.replace(/'/g, '').replace(/-/g, ' ');
    
    const replacements = {
      'MITCHELL T': 'MITCH T',
      'ROBBY ANDERSON': 'ROBBIE ANDERSON',
      'WILLIAM ': 'WILL ',
      'OLABISI': 'BISI',
      'ELI MITCHELL': 'ELIJAH MITCHELL',
      'CADILLAC WILLIAMS': 'CARNELL WILLIAMS',
      'GABE DAVIS': 'GABRIEL DAVIS',
      'JEFFERY ': 'JEFF ',
      'JOSHUA ': 'JOSH ',
      'CHAUNCEY GARDNER': 'CJ GARDNER',
      'BENNETT SKOWRONEK': 'BEN SKOWRONEK',
      'NATHANIEL DELL': 'TANK DELL'
    };
    
    for (const [old, newStr] of Object.entries(replacements)) {
      name = name.replace(old, newStr);
    }
    
    if (name.startsWith('MICHAEL ')) {
      name = name.replace('MICHAEL ', 'MIKE ', 1);
    }
    if (name.startsWith('KENNETH ')) {
      name = name.replace('KENNETH ', 'KEN ', 1);
    }
    
    return name;
  }
  
  async loadPublicADP() {
    // Try multiple methods to load public ADP
    const methods = [
      // Method 1: CORS proxy (allorigins)
      async () => {
        const corsProxy = 'https://api.allorigins.win/raw?url=';
        const apiUrl = 'https://fantasyfootballcalculator.com/api/v1/adp/ppr?teams=10&year=2025&position=all';
        const response = await fetch(corsProxy + encodeURIComponent(apiUrl));
        return await response.json();
      },
      // Method 2: Another CORS proxy
      async () => {
        const corsProxy = 'https://corsproxy.io/?';
        const apiUrl = 'https://fantasyfootballcalculator.com/api/v1/adp/ppr?teams=10&year=2025&position=all';
        const response = await fetch(corsProxy + encodeURIComponent(apiUrl));
        return await response.json();
      },
      // Method 3: Static fallback file
      async () => {
        const response = await fetch('web_static/public_adp.json');
        return await response.json();
      }
    ];
    
    for (const method of methods) {
      try {
        const data = await method();
        
        if (data && (data.status === 'Success' || data.players)) {
          // Convert the API data to our format
          const players = data.players.map((p, index) => {
            const formattedName = this.formatName(p.name);
            return {
              id: `public-${index}`,
              name: formattedName,
              position: p.position || 'UNK',
              team: p.team || 'FA',
              adp: parseFloat(p.adp) || 999,
              rank: index + 1,
              projection: 0,
              bye_week: p.bye || 0,
              var: 0,
              points_2024: 0
            };
          });
          
          // Sort by ADP
          players.sort((a, b) => a.adp - b.adp);
          console.log('Successfully loaded public ADP');
          return { players };
        }
      } catch (error) {
        console.log('Method failed, trying next:', error.message);
      }
    }
    
    console.error('All methods to load public ADP failed');
    return null;
  }
  
  async loadPlayers() {
    // Always load the complete players data from players_data.json
    // This file already has custom ADP values applied by regenerate_players_data.py
    try {
      const response = await fetch('web_static/players_data.json');
      const data = await response.json();
      
      // Use the unique_id field for consistent identification
      this.allPlayers = data.players.map((p, index) => ({
        ...p,
        id: p.unique_id || `${p.name}-${p.position}-${index}`
      }));
      
      console.log(`Loaded ${this.allPlayers.length} players`);
      
      // If admin mode, optionally load public ADP for comparison
      if (!this.adminMode) {
        const publicData = await this.loadPublicADP();
        if (publicData && publicData.players) {
          // In non-admin mode, override ADPs with public values where available
          const publicADPMap = {};
          publicData.players.forEach(p => {
            publicADPMap[p.name] = p.adp;
          });
          
          this.allPlayers.forEach(p => {
            if (publicADPMap[p.name] !== undefined) {
              p.adp = publicADPMap[p.name];
            }
          });
          console.log('Applied public ADP values in non-admin mode');
        }
      }
      
      // Sort by ADP initially
      this.allPlayers.sort((a, b) => (a.adp || 999) - (b.adp || 999));
      
      // Create available players list
      this.availablePlayers = [...this.allPlayers];
      
    } catch (error) {
      console.error('Error loading players:', error);
      this.allPlayers = [];
      this.availablePlayers = [];
    }
    
    console.log(`Using ${this.adminMode ? 'custom' : 'public'} ADP with ${this.allPlayers.length} players`);
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
      // Round 1: 1-10 (normal)
      // Round 2: 10-1 (reversed)
      // Round 3: 10-1 (reversed - this is the 3rd round reversal!)
      // Round 4: 1-10 (normal)
      // Round 5: 10-1 (reversed)
      // Round 6: 1-10 (normal)
      // Pattern: 1=normal, 2=reverse, 3=reverse, then alternating starting with 4=normal
      if (round === 2 || round === 3) {
        // Rounds 2 AND 3 are reversed (3rd round reversal)
        order.reverse();
      } else if (round >= 4) {
        // From round 4 onwards: even rounds normal, odd rounds reversed
        if (round % 2 === 1) {
          order.reverse();
        }
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
    
    // In auto mode, only allow user to pick on their turn
    // In manual mode, user can make all picks
    if (!this.manualMode && this.getCurrentTeam() !== this.userTeamId) {
      alert("It's not your turn! Switch to manual mode to make all picks.");
      return false;
    }
    
    // Debug logging
    console.log(`makePick called with ID: ${playerId}`);
    
    // Unescape the ID (in case it was escaped for HTML)
    const unescapedId = playerId.replace(/\\'/g, "'").replace(/\\"/g, '"');
    
    // Convert to string for comparison since IDs might be mixed types
    const playerIdStr = String(unescapedId);
    const playerIndex = this.availablePlayers.findIndex(p => String(p.id) === playerIdStr);
    if (playerIndex === -1) {
      console.error(`Player not found with ID: ${playerId}`);
      console.log('Available player IDs:', this.availablePlayers.slice(0, 5).map(p => ({ name: p.name, id: p.id })));
      return false;
    }
    
    const player = this.availablePlayers[playerIndex];
    console.log(`Found player: ${player.name} at index ${playerIndex}`);
    const teamId = this.getCurrentTeam();
    const team = this.teams[teamId];
    
    // Add to team roster
    team.roster.push(player);
    team.positionCounts[player.position] = (team.positionCounts[player.position] || 0) + 1;
    
    // Remove from available - use splice to maintain array integrity
    this.availablePlayers.splice(playerIndex, 1);
    
    this.draftedPlayers.push({
      pick: this.currentPick,
      teamId: teamId,
      player: player
    });
    
    this.currentPick++;
    
    // Save state to localStorage
    this.saveState();
    
    // Auto-pick for computer teams only if not in manual mode
    // In manual mode, don't auto-pick at all
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
    
    // Convert to string for comparison since IDs might be mixed types
    this.availablePlayers = this.availablePlayers.filter(p => String(p.id) !== String(player.id));
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
    if ((counts.K || 0) < this.rosterSpots.K && this.currentPick > 120) needs.push('K');
    if ((counts.DST || 0) < this.rosterSpots.DST && this.currentPick > 130) needs.push('DST');
    
    return needs;
  }

  rollback() {
    if (this.draftedPlayers.length === 0) return;
    
    const lastPick = this.draftedPlayers.pop();
    const team = this.teams[lastPick.teamId];
    
    // Remove from team roster using name and position for unique identification
    // (IDs are not unique in the data)
    team.roster = team.roster.filter(p => 
      !(p.name === lastPick.player.name && p.position === lastPick.player.position)
    );
    team.positionCounts[lastPick.player.position]--;
    
    // Add back to available
    this.availablePlayers.push(lastPick.player);
    
    // Re-sort using current sort method
    if (this.sortBy === 'adp') {
      this.availablePlayers.sort((a, b) => (a.adp || 999) - (b.adp || 999));
    } else if (this.sortBy === 'var') {
      this.availablePlayers.sort((a, b) => {
        const varA = parseFloat(a.var) || -999;
        const varB = parseFloat(b.var) || -999;
        return varB - varA;
      });
    } else if (this.sortBy === 'nfc') {
      this.availablePlayers.sort((a, b) => (a.nfc_adp || 999) - (b.nfc_adp || 999));
    }
    
    this.currentPick--;
    this.saveState();
    this.render();
  }

  async toggleAdminMode(password) {
    if (password === 'xyz') {
      this.adminMode = !this.adminMode;
      console.log(`Admin mode ${this.adminMode ? 'enabled' : 'disabled'}`);
      
      // Reload players with appropriate ADP
      await this.loadPlayers();
      
      // If draft is in progress, restore draft state
      if (this.draftStarted && this.draftedPlayers.length > 0) {
        // Use player names to match since IDs change between reloads
        const draftedNames = new Set(this.draftedPlayers.map(d => `${d.player.name}-${d.player.position}`));
        this.availablePlayers = this.allPlayers.filter(p => !draftedNames.has(`${p.name}-${p.position}`));
        
        // Update draftedPlayers with new player objects that have correct IDs
        this.draftedPlayers = this.draftedPlayers.map(dp => {
          const newPlayer = this.allPlayers.find(p => p.name === dp.player.name && p.position === dp.player.position);
          return {
            ...dp,
            player: newPlayer || dp.player
          };
        });
        
        // Re-sort available players
        if (this.sortBy === 'adp') {
          this.availablePlayers.sort((a, b) => (a.adp || 999) - (b.adp || 999));
        } else if (this.sortBy === 'var') {
          this.availablePlayers.sort((a, b) => {
            const varA = parseFloat(a.var) || -999;
            const varB = parseFloat(b.var) || -999;
            return varB - varA;
          });
        } else if (this.sortBy === 'nfc') {
          this.availablePlayers.sort((a, b) => (a.nfc_adp || 999) - (b.nfc_adp || 999));
        }
      }
      
      this.saveState();
      this.render();
      return true;
    }
    return false;
  }
  
  restart() {
    // Make a fresh copy of all players
    this.availablePlayers = [...this.allPlayers];
    this.draftedPlayers = [];
    this.currentPick = 1;
    this.userTeamId = null;
    this.draftStarted = false;
    this.manualMode = true; // Reset to manual mode
    this.initializeTeams();
    
    // Re-sort based on current sort preference
    if (this.sortBy === 'adp') {
      this.availablePlayers.sort((a, b) => (a.adp || 999) - (b.adp || 999));
    } else if (this.sortBy === 'var') {
      this.availablePlayers.sort((a, b) => {
        const varA = parseFloat(a.var) || -999;
        const varB = parseFloat(b.var) || -999;
        return varB - varA;
      });
    } else if (this.sortBy === 'nfc') {
      this.availablePlayers.sort((a, b) => (a.nfc_adp || 999) - (b.nfc_adp || 999));
    }
    
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
      manualMode: this.manualMode,
      positionFilter: this.positionFilter,
      sortBy: this.sortBy || 'adp',
      adminMode: this.adminMode
    };
    localStorage.setItem('draftState', JSON.stringify(state));
    localStorage.setItem('playersData', JSON.stringify({ players: this.allPlayers }));
  }

  loadState() {
    const state = localStorage.getItem('draftState');
    if (state) {
      const data = JSON.parse(state);
      this.currentPick = data.currentPick;
      this.draftedPlayers = data.draftedPlayers || [];
      this.teams = data.teams;
      this.userTeamId = data.userTeamId;
      this.draftStarted = data.draftStarted;
      this.manualMode = data.manualMode !== undefined ? data.manualMode : true;
      this.positionFilter = data.positionFilter || 'ALL';
      this.sortBy = data.sortBy || 'adp';
      this.adminMode = data.adminMode || false;
      
      // Rebuild available players - use name matching as fallback
      const draftedNames = new Set(this.draftedPlayers.map(d => d.player.name));
      const draftedIds = new Set(this.draftedPlayers.map(d => String(d.player.id)));
      
      // Filter using both ID and name to be safe
      this.availablePlayers = this.allPlayers.filter(p => {
        return !draftedIds.has(String(p.id)) && !draftedNames.has(p.name);
      });
      
      // Re-sort available players based on current sort
      if (this.sortBy === 'adp') {
        this.availablePlayers.sort((a, b) => (a.adp || 999) - (b.adp || 999));
      } else if (this.sortBy === 'var') {
        this.availablePlayers.sort((a, b) => {
          const varA = parseFloat(a.var) || -999;
          const varB = parseFloat(b.var) || -999;
          return varB - varA;
        });
      } else if (this.sortBy === 'nfc') {
        this.availablePlayers.sort((a, b) => (a.nfc_adp || 999) - (b.nfc_adp || 999));
      }
      
      console.log(`Loaded state: ${this.availablePlayers.length} available, ${this.draftedPlayers.length} drafted`);
      
      // Resume auto-picking if needed (only if in auto mode)
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
        // Show draft spot selection with admin status
        let spotsHtml = '<div style="padding: 5px;">';
        spotsHtml += `<div style="font-size: 14px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">`;
        spotsHtml += `<span>Select Draft Position:</span>`;
        spotsHtml += `<span style="font-size: 11px; color: ${this.adminMode ? '#50fa7b' : '#888'};">ADP: ${this.adminMode ? 'Custom' : 'Public'}</span>`;
        spotsHtml += `</div>`;
        spotsHtml += '<div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 5px;">';
        for (let i = 1; i <= this.numTeams; i++) {
          spotsHtml += `<button onclick="draft.selectDraftSpot(${i})" style="padding: 15px; font-size: 16px;">${i}</button>`;
        }
        spotsHtml += '</div></div>';
        statusEl.innerHTML = spotsHtml;
      } else {
        const currentTeam = this.getCurrentTeam();
        const isUserPick = currentTeam === this.userTeamId;
        
        // Position filter buttons - all on one row
        const positions = ['ALL', 'QB', 'RB', 'WR', 'TE', 'FLEX', 'LB', 'DB', 'K', 'DST'];
        
        const filterButtons = positions.map(pos => 
          `<button onclick="draft.setPositionFilter('${pos}')" 
            style="padding: 3px 6px; font-size: 10px; background: ${this.positionFilter === pos ? '#50fa7b' : '#333'}; 
            color: ${this.positionFilter === pos ? '#000' : '#fff'}; border: none; border-radius: 2px;">${pos}</button>`
        ).join('');
        
        // Sort controls - only show VAR and NFC in admin mode
        const sortOptions = this.adminMode ? ['ADP', 'VAR', 'NFC'] : ['ADP'];
        const sortButtons = sortOptions.map(sort => {
          const sortValue = sort.toLowerCase();
          return `<button onclick="draft.setSortBy('${sortValue}')" 
            style="padding: 3px 8px; font-size: 10px; background: ${this.sortBy === sortValue ? '#50fa7b' : '#444'}; 
            color: ${this.sortBy === sortValue ? '#000' : '#fff'}; border: none; border-radius: 2px; margin: 0 1px;">${sort}</button>`;
        }).join('');
        
        // Create draft grid visualization
        const currentRound = Math.ceil(this.currentPick / this.numTeams);
        const teamPicking = this.draftOrder[this.currentPick - 1];
        
        // Determine if round goes forward or backward
        // Round 1: forward (teams 1→10)
        // Round 2: backward (teams 10→1) 
        // Round 3: backward (teams 10→1) - 3rd round reversal
        // Round 4: forward (teams 1→10)
        // etc.
        const isRoundReversed = (currentRound % 2 === 0 && currentRound !== 3) || (currentRound === 3);
        
        // Build grid for current and next round
        let gridHtml = '<div style="display: flex; flex-direction: column; gap: 1px; margin: 0 5px;">';
        
        // Show current round
        gridHtml += '<div style="display: flex; gap: 1px; align-items: center;">';
        if (isRoundReversed) {
          gridHtml += '<span style="font-size: 10px; color: #888;">←</span>';
          // Show teams 10 to 1 from left to right
          for (let teamNum = 10; teamNum >= 1; teamNum--) {
            const isPick = (teamNum === teamPicking);
            gridHtml += `<div style="width: 8px; height: 8px; background: ${isPick ? '#50fa7b' : '#333'}; border-radius: 1px;"></div>`;
          }
        } else {
          // Show teams 1 to 10 from left to right
          for (let teamNum = 1; teamNum <= 10; teamNum++) {
            const isPick = (teamNum === teamPicking);
            gridHtml += `<div style="width: 8px; height: 8px; background: ${isPick ? '#50fa7b' : '#333'}; border-radius: 1px;"></div>`;
          }
          gridHtml += '<span style="font-size: 10px; color: #888;">→</span>';
        }
        gridHtml += '</div>';
        
        // Show next round preview (dimmer)
        if (currentRound < 25) {
          const nextRound = currentRound + 1;
          const nextRoundReversed = (nextRound % 2 === 0 && nextRound !== 3) || (nextRound === 3);
          gridHtml += '<div style="display: flex; gap: 1px; align-items: center; opacity: 0.3;">';
          if (nextRoundReversed) {
            gridHtml += '<span style="font-size: 10px; color: #888;">←</span>';
            for (let i = 10; i >= 1; i--) {
              gridHtml += `<div style="width: 8px; height: 8px; background: #333; border-radius: 1px;"></div>`;
            }
          } else {
            for (let i = 1; i <= 10; i++) {
              gridHtml += `<div style="width: 8px; height: 8px; background: #333; border-radius: 1px;"></div>`;
            }
            gridHtml += '<span style="font-size: 10px; color: #888;">→</span>';
          }
          gridHtml += '</div>';
        }
        gridHtml += '</div>';
        
        statusEl.innerHTML = `
          <div style="display: flex; flex-direction: column; gap: 3px; padding: 3px;">
            <div style="display: flex; justify-content: space-between; align-items: center; gap: 5px;">
              <span style="white-space: nowrap; font-size: 12px;"><strong>P${this.currentPick}</strong></span>
              <span style="font-size: 10px; color: ${this.adminMode ? '#50fa7b' : '#888'};">${this.adminMode ? 'CUSTOM' : 'PUBLIC'}</span>
              <div style="display: flex; gap: 2px;">
                ${sortButtons}
              </div>
              ${gridHtml}
              <span style="background: ${isUserPick ? '#2a4e2a' : 'transparent'}; padding: 2px 6px; border-radius: 3px; white-space: nowrap; font-size: 12px;">
                ${isUserPick ? 'YOU' : `T${currentTeam}`}
              </span>
              ${!isUserPick && this.manualMode ? '<button onclick="draft.makeAutoPick()" style="padding: 2px 8px; font-size: 11px;">CPU</button>' : ''}
            </div>
            <div style="display: flex; gap: 2px; justify-content: center;">
              ${filterButtons}
            </div>
          </div>
        `;
      }
    }

    // Update available players
    this.renderAvailablePlayers();
    
    // Update draft board
    this.renderDraftBoard();
    this.renderDraftBoard('draft-board-mini', 25); // Mini board showing all rounds
    
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
      DB: '#f1fa8c',
      K: '#e879f9',
      DST: '#a78bfa',
      DEF: '#a78bfa'  // Some data might use DEF instead of DST
    };
    
    // Add sort buttons header
    let headerHtml = `
      <div style="display: flex; justify-content: space-between; padding: 5px 8px; background: #2a2d33; border-bottom: 2px solid #444;">
        <div style="display: flex; gap: 10px;">
          <button onclick="draft.setSortBy('adp')" 
            style="padding: 3px 8px; font-size: 11px; background: ${this.sortBy === 'adp' ? '#50fa7b' : '#444'}; 
            color: ${this.sortBy === 'adp' ? '#000' : '#fff'}; border: none; border-radius: 3px;">
            ADP ↑
          </button>
          ${this.adminMode ? `
          <button onclick="draft.setSortBy('var')" 
            style="padding: 3px 8px; font-size: 11px; background: ${this.sortBy === 'var' ? '#50fa7b' : '#444'}; 
            color: ${this.sortBy === 'var' ? '#000' : '#fff'}; border: none; border-radius: 3px;">
            VAR ↓
          </button>` : ''}
        </div>
        <div style="font-size: 11px; color: #888;">
          ${this.availablePlayers.length} available
        </div>
      </div>
    `;
    
    // Filter players by position
    let filteredPlayers = this.availablePlayers;
    if (this.positionFilter !== 'ALL') {
      if (this.positionFilter === 'FLEX') {
        // FLEX includes RB, WR, TE
        filteredPlayers = this.availablePlayers.filter(p => 
          p.position === 'RB' || p.position === 'WR' || p.position === 'TE'
        );
      } else {
        // Filter by specific position
        filteredPlayers = this.availablePlayers.filter(p => p.position === this.positionFilter);
      }
    }
    
    // In manual mode, always allow clicking
    // In auto mode, only allow clicking on user's turn
    const canPick = this.manualMode || (this.draftStarted && this.getCurrentTeam() === this.userTeamId);
    const cursorStyle = canPick ? 'cursor: pointer;' : 'cursor: not-allowed; opacity: 0.7;';

    const html = filteredPlayers.map(player => {
      // Escape the ID for safe use in onclick attribute
      const escapedId = (player.id || '').replace(/'/g, "\\'").replace(/"/g, '\\"');
      return `
        <div class="player-row" onclick="draft.makePick('${escapedId}')" style="${cursorStyle} padding: 8px; border-bottom: 1px solid #333; display: flex; justify-content: space-between; align-items: center;">
          <div style="flex: 1;">
            <span style="color: ${positionColors[player.position] || '#fff'}; font-weight: bold; margin-right: 10px;">${player.position}</span>
            <span>${player.name}</span>
            <span style="color: #888; margin-left: 10px;">${player.team}</span>
          </div>
          <div>
            ${this.adminMode && this.sortBy === 'var' ? 
              `<span style="color: #50fa7b;">VAR: ${player.var ? player.var.toFixed(1) : '0.0'}</span>` :
              this.adminMode && this.sortBy === 'nfc' ?
              `<span style="color: #ff79c6;">NFC: ${player.nfc_adp ? player.nfc_adp.toFixed(1) : '999'}</span>` :
              `<span style="color: #888;">ADP: ${player.adp}</span>`
            }
          </div>
        </div>
      `;
    }).join('');

    container.innerHTML = headerHtml + html;
  }

  renderDraftBoard(elementId = 'draft-board', maxRounds = 5) {
    const container = document.getElementById(elementId);
    if (!container) return;

    const rounds = Math.ceil(this.totalPicks / this.numTeams);
    let html = '<table style="width: 100%; border-collapse: collapse;">';
    html += '<thead><tr><th style="padding: 3px; border: 1px solid #333; font-size: 11px;">R</th>';
    
    for (let i = 1; i <= this.numTeams; i++) {
      const fontSize = elementId === 'draft-board-mini' ? '10px' : '12px';
      html += `<th style="padding: 3px; border: 1px solid #333; font-size: ${fontSize};">T${i}</th>`;
    }
    html += '</tr></thead><tbody>';

    for (let round = 1; round <= Math.min(rounds, maxRounds); round++) {
      html += `<tr><td style="padding: 3px; border: 1px solid #333; font-weight: bold; font-size: 10px;">${round}</td>`;
      
      for (let team = 1; team <= this.numTeams; team++) {
        const pick = this.draftedPlayers.find(p => {
          const pickRound = Math.ceil(p.pick / this.numTeams);
          const pickTeam = this.draftOrder[p.pick - 1];
          return pickRound === round && pickTeam === team;
        });
        
        const fontSize = elementId === 'draft-board-mini' ? '9px' : '12px';
        const padding = elementId === 'draft-board-mini' ? '2px' : '5px';
        html += `<td style="padding: ${padding}; border: 1px solid #333; font-size: ${fontSize};">`;
        if (pick) {
          let displayName = '';
          const fullName = pick.player.name.toUpperCase();
          
          // Special abbreviations for common players
          if (fullName.includes('MCCAFFREY')) {
            displayName = 'CMC';
          } else if (fullName.includes('JUSTIN JEFFERSON')) {
            displayName = 'JJ';
          } else if (fullName.includes('BIJAN')) {
            displayName = 'BIJAN';
          } else if (fullName.includes('MCCONKEY')) {
            displayName = 'LADD';
          } else if (fullName.includes('BRIAN THOMAS')) {
            displayName = 'BTJ';
          } else if (fullName.includes('CALVIN RIDLEY')) {
            displayName = 'RIDLY';
          } else if (fullName.includes('MARVIN HARRISON')) {
            displayName = 'MHJ';
          } else if (fullName.includes('AMON-RA') || fullName.includes('AMON RA')) {
            displayName = 'ARSB';
          } else if (fullName.includes('DEANDRE HOPKINS')) {
            displayName = 'DHOP';
          } else if (fullName.includes('KENNETH WALKER')) {
            displayName = 'KW3';
          } else if (fullName.includes('TRAVIS ETIENNE')) {
            displayName = 'ETN';
          } else if (fullName.includes('RACHAAD WHITE')) {
            displayName = 'RWHIT';
          } else if (fullName.includes('TYREEK HILL')) {
            displayName = 'HILL';
          } else if (fullName.includes('DAVANTE ADAMS')) {
            displayName = 'ADAMS';
          } else if (fullName.includes('JAMARR CHASE') || fullName.includes("JA'MARR")) {
            displayName = 'CHASE';
          } else if (fullName.includes('GEORGE PICKENS')) {
            displayName = 'PICK';
          } else if (fullName.includes('JONATHAN TAYLOR')) {
            displayName = 'JT';
          } else if (fullName.includes('SAQUON')) {
            displayName = 'SAQON';
          } else if (fullName.includes('DERRICK HENRY')) {
            displayName = 'HENRY';
          } else if (fullName.includes('JOSH JACOBS')) {
            displayName = 'JACBS';
          } else if (fullName.includes('ALVIN KAMARA')) {
            displayName = 'AK';
          } else if (fullName.includes('BREECE HALL')) {
            displayName = 'HALL';
          } else if (fullName.includes('JAHMYR GIBBS')) {
            displayName = 'GIBBS';
          } else if (fullName.includes('DEVON ACHANE') || fullName.includes("DE'VON")) {
            displayName = 'ACHAN';
          } else if (fullName.includes('JAMES COOK')) {
            displayName = 'COOK';
          } else if (fullName.includes('JOE MIXON')) {
            displayName = 'MIXON';
          } else if (fullName.includes('GARRETT WILSON')) {
            displayName = 'GWILS';
          } else if (fullName.includes('CHRIS OLAVE')) {
            displayName = 'OLAVE';
          } else if (fullName.includes('MIKE EVANS')) {
            displayName = 'EVANS';
          } else if (fullName.includes('PUKA NACUA')) {
            displayName = 'PUKA';
          } else if (fullName.includes('NICO COLLINS')) {
            displayName = 'NICO';
          } else if (fullName.includes('BRANDON AIYUK')) {
            displayName = 'AIYUK';
          } else if (fullName.includes('DEEBO SAMUEL')) {
            displayName = 'DEEBO';
          } else if (fullName.includes('STEFON DIGGS')) {
            displayName = 'DIGGS';
          } else if (fullName.includes('COOPER KUPP')) {
            displayName = 'KUPP';
          } else if (fullName.includes('CEEDEE LAMB')) {
            displayName = 'LAMB';
          } else if (fullName.includes('AJ BROWN') || fullName.includes('A.J.')) {
            displayName = 'AJB';
          } else if (fullName.includes('DK METCALF')) {
            displayName = 'DK';
          } else if (fullName.includes('JAYLEN WADDLE')) {
            displayName = 'WADL';
          } else if (fullName.includes('DJ MOORE')) {
            displayName = 'DJM';
          } else if (fullName.includes('TRAVIS KELCE')) {
            displayName = 'KELCE';
          } else if (fullName.includes('SAM LAPORTA')) {
            displayName = 'SAMMY';
          } else if (fullName.includes('MARK ANDREWS')) {
            displayName = 'MANDR';
          } else if (fullName.includes('GEORGE KITTLE')) {
            displayName = 'KITTL';
          } else if (fullName.includes('TREY MCBRIDE')) {
            displayName = 'MCBRD';
          } else if (fullName.includes('DALTON KINCAID')) {
            displayName = 'KINCA';
          } else if (fullName.includes('TJ HOCKENSON') || fullName.includes('T.J.')) {
            displayName = 'HOCK';
          } else if (fullName.includes('KYLE PITTS')) {
            displayName = 'PITTS';
          } else if (fullName.includes('EVAN ENGRAM')) {
            displayName = 'ENGRM';
          } else if (fullName.includes('DALLAS GOEDERT')) {
            displayName = 'GOED';
          } else if (fullName.includes('D/ST') || fullName.includes('DST')) {
            // For defenses, use team abbreviation
            displayName = pick.player.team;
          } else {
            // Default: use last name, max 5 chars
            const lastName = pick.player.name.split(' ').pop();
            displayName = lastName.substring(0, 5).toUpperCase();
          }
          
          // For mini board, ensure it's max 5 chars
          if (elementId === 'draft-board-mini' && displayName.length > 5) {
            displayName = displayName.substring(0, 5);
          }
          
          html += `${pick.player.position} ${displayName}`;
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
    ['QB', 'RB', 'WR', 'TE', 'LB', 'DB', 'K', 'DST'].forEach(pos => {
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