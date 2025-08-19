// Draft Logic Module

class DraftManager {
    constructor() {
        this.players = [];
        this.availablePlayers = [];
        this.draftedPlayers = [];
        this.teams = {};
        this.draftOrder = [];
        this.currentPick = 1;
        this.userTeamId = null;
        this.customADP = {};
        this.sosData = {}; // Store SOS data
        this.trades = [];
        this.draftHistory = [];
        this.timerSeconds = CONFIG.DEFAULT_TIMER_SECONDS;
        this.timerInterval = null;
        this.currentTimer = 0;
        this.autoPickEnabled = false;
        this.adminMode = false;
        this.usePrivateADP = true; // Start with private ADP (uses custom values)
        this.privatePlayersData = null; // Store private/custom ADP
        this.publicPlayersData = null; // Store public ADP
        
        this.initializeTeams();
        // Don't load customADP from localStorage - we load from file instead
        // this.loadCustomADP();
        this.draftOrder = utils.calculateDraftOrder(CONFIG.NUM_TEAMS, CONFIG.NUM_ROUNDS);
    }
    
    initializeTeams() {
        for (let i = 0; i < CONFIG.NUM_TEAMS; i++) {
            this.teams[i] = {
                id: i,
                name: CONFIG.TEAM_NAMES[i],
                picks: [],
                roster: {
                    QB: [],
                    RB: [],
                    WR: [],
                    TE: [],
                    LB: [],
                    DB: []
                }
            };
        }
    }
    
    estimateFantasyPoints(position, adp) {
        // Estimate fantasy points based on position and ADP
        // These are rough estimates to make VAR calculations work
        const basePoints = {
            QB: 300,
            RB: 200,
            WR: 180,
            TE: 140,
            LB: 120,
            DB: 100
        };
        
        const base = basePoints[position] || 100;
        // Decay based on ADP
        const decay = Math.max(0, 1 - (adp / 200));
        return Math.round(base * decay);
    }
    
    async loadPublicADP() {
        // Try to load public ADP from Fantasy Football Calculator via CORS proxy
        const corsProxies = [
            'https://api.allorigins.win/raw?url=',
            'https://corsproxy.io/?'
        ];
        const apiUrl = 'https://fantasyfootballcalculator.com/api/v1/adp/ppr?teams=10&year=2025&position=all';
        
        for (const proxy of corsProxies) {
            try {
                const response = await fetch(proxy + encodeURIComponent(apiUrl));
                const data = await response.json();
                if (data && data.players) {
                    return data.players.map((p, idx) => ({
                        player_id: `public-${idx}`,
                        name: p.name,
                        first_name: p.name.split(' ')[0] || '',
                        last_name: p.name.split(' ').slice(1).join(' ') || '',
                        position: p.position || 'UNK',
                        team: p.team || 'FA',
                        adp: parseFloat(p.adp) || 999,
                        rank: idx + 1
                    }));
                }
            } catch (e) {
                console.log('CORS proxy failed:', proxy);
            }
        }
        
        // Fallback: generate garbage ADP data
        console.log('Using fallback public ADP data');
        const positions = ['QB', 'RB', 'WR', 'TE'];
        const players = [];
        let adp = 1;
        
        for (let i = 0; i < 200; i++) {
            const pos = positions[Math.floor(Math.random() * positions.length)];
            players.push({
                player_id: `fallback-${i}`,
                name: `Player ${i + 1}`,
                first_name: `Player`,
                last_name: `${i + 1}`,
                position: pos,
                team: 'FA',
                adp: adp + Math.random() * 2,
                rank: i + 1
            });
            adp += 1.5;
        }
        
        return players;
    }
    
    async loadSOSData() {
        try {
            const response = await fetch('data/strength_of_schedule.csv');
            const csvText = await response.text();
            const lines = csvText.split('\n');
            const headers = lines[0].split(',');
            
            for (let i = 1; i < lines.length; i++) {
                const values = lines[i].split(',');
                if (values.length > 1) {
                    const team = values[0];
                    this.sosData[team] = {
                        QB: parseInt(values[1]),
                        RB: parseInt(values[2]),
                        WR: parseInt(values[3]),
                        TE: parseInt(values[4])
                    };
                }
            }
            console.log('Loaded SOS data for', Object.keys(this.sosData).length, 'teams');
        } catch (e) {
            console.error('Failed to load SOS data:', e);
        }
    }
    
    async loadPlayers() {
        try {
            // Load SOS data first
            await this.loadSOSData();
            
            // Load custom ADP edits (same file as desktop version)
            try {
                const customAdpResponse = await fetch('data/custom_adp.json');
                if (customAdpResponse.ok) {
                    const customAdpData = await customAdpResponse.json();
                    console.log('Loading custom ADP data from file...');
                    console.log('customAdpData type:', typeof customAdpData);
                    console.log('customAdpData keys:', Object.keys(customAdpData).slice(0, 10));
                    
                    // Clear any existing data first
                    this.customADP = {};
                    
                    for (const [playerId, adpValue] of Object.entries(customAdpData)) {
                        this.customADP[playerId] = adpValue;
                    }
                    console.log('Custom ADP loaded:', Object.keys(this.customADP).length, 'entries');
                    console.log('Drake London (8112) custom ADP after loading:', this.customADP['8112']);
                    console.log('Type of key "8112":', typeof "8112");
                    console.log('customADP has "8112"?:', "8112" in this.customADP);
                    console.log('First 5 custom ADP entries:', Object.entries(this.customADP).slice(0, 5));
                } else {
                    console.error('Failed to fetch custom_adp.json, status:', customAdpResponse.status);
                }
            } catch (e) {
                console.error('Failed to load custom ADP:', e);
            }
            
            // Load base ADP data from players_2025.json
            try {
                const response = await fetch('data/players_2025.json');
                const data = await response.json();
                const basePlayersData = data.players || data;
                
                // Use the same base data for both modes
                this.privatePlayersData = basePlayersData;
                this.publicPlayersData = basePlayersData;
                
                console.log('Loaded base ADP data, player count:', basePlayersData.length);
            } catch (e) {
                console.error('Failed to load base ADP data:', e);
                return false;
            }
            
            // Always use the same player data
            const playersArray = this.privatePlayersData;
            
            this.players = playersArray.map(p => {
                // Parse first and last name from the full name
                const nameParts = (p.name || '').split(' ');
                const firstName = nameParts[0] || '';
                const lastName = nameParts.slice(1).join(' ') || '';
                
                // Generate estimated fantasy points based on ADP
                const estimatedPoints = this.estimateFantasyPoints(p.position, p.adp || p.rank || 999);
                
                // Store original ADP
                const originalADP = p.adp || 999;
                
                // Apply custom ADP ONLY when using private ADP
                let finalADP = originalADP;
                const customValue = this.customADP[p.player_id];
                if (this.usePrivateADP && customValue !== undefined) {
                    finalADP = customValue;
                    if (p.name === 'Drake London') {
                        console.log(`>>> INITIAL LOAD APPLYING CUSTOM ADP: ${originalADP} -> ${customValue}`);
                    }
                }
                
                // Debug Drake London specifically
                if (p.name && p.name.includes('Drake London')) {
                    console.log('DRAKE LONDON DEBUG IN LOAD:', {
                        name: p.name,
                        player_id: p.player_id,
                        base_adp: originalADP,
                        custom_adp: this.customADP[p.player_id],
                        usePrivateADP: this.usePrivateADP,
                        finalADP: finalADP
                    });
                }
                
                // Get real SOS from data (not random!)
                const sosValue = this.sosData[p.team] ? this.sosData[p.team][p.position] : null;
                
                return {
                    ...p,
                    first_name: p.first_name || firstName,
                    last_name: p.last_name || lastName,
                    adp: finalADP,
                    drafted: false,
                    draftedBy: null,
                    draftedAt: null,
                    original_adp: originalADP,
                    // Default values for missing properties
                    tier: p.tier || Math.ceil(originalADP / 12) || 1,
                    sos: sosValue || p.sos || null, // Use real SOS data
                    projected_rank: p.projected_rank || `${p.position}${Math.ceil(originalADP / CONFIG.NUM_TEAMS)}`,
                    projected_points: p.projected_points || estimatedPoints,
                    var: 0 // Will be calculated after all players are loaded
                };
            });
            
            // Don't apply custom ADP here since it's already applied above when appropriate
            // this.applyCustomADP();
            
            // Sort by ADP
            this.players.sort((a, b) => (a.adp || 999) - (b.adp || 999));
            
            // Initialize available players
            this.availablePlayers = [...this.players];
            
            // Calculate VAR for all players
            this.calculateAllVAR();
            
            // Debug logging
            const drakeLondon = this.players.find(p => p.name === 'Drake London');
            console.log(`Loaded ${this.players.length} players for ${this.usePrivateADP ? 'PRIVATE' : 'PUBLIC'} ADP mode`);
            console.log('Drake London after initial load:', drakeLondon ? {
                name: drakeLondon.name,
                player_id: drakeLondon.player_id,
                adp: drakeLondon.adp,
                original_adp: drakeLondon.original_adp
            } : 'NOT FOUND');
            console.log('Custom ADP data loaded:', Object.keys(this.customADP).length, 'entries');
            console.log('Custom ADP for 8112:', this.customADP['8112']);
            
            return true;
        } catch (error) {
            console.error('Error loading players:', error);
            return false;
        }
    }
    
    calculateAllVAR() {
        // Group players by position
        const playersByPosition = {};
        
        for (const player of this.players) {
            if (!playersByPosition[player.position]) {
                playersByPosition[player.position] = [];
            }
            playersByPosition[player.position].push(player);
        }
        
        // Sort each position by projected points
        for (const position in playersByPosition) {
            playersByPosition[position].sort((a, b) => 
                (b.projected_points || 0) - (a.projected_points || 0)
            );
        }
        
        // Calculate VAR for each player
        for (const player of this.players) {
            player.var = utils.calculateVAR(player, playersByPosition);
        }
    }
    
    loadCustomADP() {
        const saved = utils.loadFromStorage('customADP');
        if (saved) {
            this.customADP = saved;
        }
    }
    
    saveCustomADP() {
        utils.saveToStorage('customADP', this.customADP);
    }
    
    applyCustomADP() {
        // This function is now deprecated since we apply custom ADP during loading
        // Keeping it for compatibility but it doesn't do anything
        console.log('applyCustomADP called but custom ADP is now applied during loading');
    }
    
    updatePlayerADP(playerId, newADP) {
        if (newADP && newADP > 0) {
            this.customADP[playerId] = newADP;
        } else {
            delete this.customADP[playerId];
        }
        
        this.saveCustomADP();
        this.applyCustomADP();
    }
    
    resetAllADP() {
        this.customADP = {};
        this.saveCustomADP();
        
        // Restore original ADP values
        for (const player of this.players) {
            player.adp = player.original_adp || player.adp;
        }
        
        this.applyCustomADP();
    }
    
    getCurrentPickInfo() {
        const { round, position } = utils.getRoundAndPosition(this.currentPick, CONFIG.NUM_TEAMS);
        const teamIndex = this.getTeamAtPosition(round, position) - 1;
        const team = this.teams[teamIndex];
        
        return {
            pickNumber: this.currentPick,
            round: round,
            position: position,
            team: team,
            isUserPick: teamIndex === this.userTeamId
        };
    }
    
    getTeamAtPosition(round, position) {
        const pickNum = utils.getPickNumber(round, position, CONFIG.NUM_TEAMS);
        const originalTeam = this.draftOrder[round - 1][position - 1];
        
        // Check for round-based trades
        for (const trade of this.trades) {
            if (trade.type === 'rounds') {
                // originalTeam is 1-indexed (1-10), trade.team1/team2 are 0-indexed (0-9)
                // So we need to compare originalTeam - 1 with trade.team1/team2
                const originalTeamIndex = originalTeam - 1;
                
                // Check if team1's pick in this round goes to team2
                if (trade.team1Rounds && trade.team1Rounds.includes(round) && originalTeamIndex === trade.team1) {
                    console.log(`Trade: Pick ${pickNum} (R${round}) goes from ${CONFIG.TEAM_NAMES[trade.team1]} to ${CONFIG.TEAM_NAMES[trade.team2]}`);
                    return trade.team2 + 1; // Convert back to 1-indexed
                }
                // Check if team2's pick in this round goes to team1
                if (trade.team2Rounds && trade.team2Rounds.includes(round) && originalTeamIndex === trade.team2) {
                    console.log(`Trade: Pick ${pickNum} (R${round}) goes from ${CONFIG.TEAM_NAMES[trade.team2]} to ${CONFIG.TEAM_NAMES[trade.team1]}`);
                    return trade.team1 + 1; // Convert back to 1-indexed
                }
            } else {
                // Old pick-based trade system
                if (trade.pick1 === pickNum) {
                    return trade.team2 + 1;
                } else if (trade.pick2 === pickNum) {
                    return trade.team1 + 1;
                }
            }
        }
        
        return originalTeam;
    }
    
    draftPlayer(player, teamId = null) {
        if (player.drafted) return false;
        
        const pickInfo = this.getCurrentPickInfo();
        const actualTeamId = teamId !== null ? teamId : pickInfo.team.id;
        
        // Mark player as drafted
        player.drafted = true;
        player.draftedBy = actualTeamId;
        player.draftedAt = this.currentPick;
        
        // Add to team roster
        const team = this.teams[actualTeamId];
        team.picks.push(player);
        team.roster[player.position].push(player);
        
        // Remove from available players
        this.availablePlayers = this.availablePlayers.filter(p => p.player_id !== player.player_id);
        
        // Add to draft history
        this.draftHistory.push({
            pick: this.currentPick,
            round: pickInfo.round,
            position: pickInfo.position,
            team: team.name,
            player: player
        });
        
        // Move to next pick
        this.currentPick++;
        
        // Stop timer if running
        this.stopTimer();
        
        return true;
    }
    
    undoLastPick() {
        if (this.draftHistory.length === 0) return false;
        
        const lastPick = this.draftHistory.pop();
        const player = lastPick.player;
        const team = this.teams[player.draftedBy];
        
        // Mark player as not drafted
        player.drafted = false;
        player.draftedBy = null;
        player.draftedAt = null;
        
        // Remove from team
        team.picks = team.picks.filter(p => p.player_id !== player.player_id);
        team.roster[player.position] = team.roster[player.position].filter(
            p => p.player_id !== player.player_id
        );
        
        // Add back to available players and re-sort
        this.availablePlayers.push(player);
        this.availablePlayers.sort((a, b) => (a.adp || 999) - (b.adp || 999));
        
        // Go back one pick
        this.currentPick--;
        
        return true;
    }
    
    selectComputerPick() {
        const pickInfo = this.getCurrentPickInfo();
        const team = pickInfo.team;
        const pickNum = this.currentPick;
        
        // Special rules for certain players
        if (pickNum <= 2) {
            const chase = this.availablePlayers.find(p => 
                p.first_name === "Ja'Marr" && p.last_name === "Chase"
            );
            if (chase) {
                return chase;
            }
        }
        
        if (pickNum <= 21) {
            const burrow = this.availablePlayers.find(p => 
                p.first_name === "Joe" && p.last_name === "Burrow"
            );
            if (burrow) {
                return burrow;
            }
        }
        
        // Check position needs
        const roster = team.roster;
        const needs = this.calculateTeamNeeds(roster);
        
        // Early picks: Just take best available
        if (pickNum <= 30) {
            return this.availablePlayers[0];
        }
        
        // Mid to late picks: Consider position needs
        let candidates = [];
        
        // If we have a critical need, prioritize it
        for (const need of needs) {
            const positionPlayers = this.availablePlayers.filter(p => p.position === need);
            if (positionPlayers.length > 0) {
                candidates.push(...positionPlayers.slice(0, 3)); // Top 3 at needed position
            }
        }
        
        // If no critical needs or late in draft, take best available
        if (candidates.length === 0 || pickNum > 100) {
            candidates = this.availablePlayers.slice(0, 5);
        }
        
        // Add some randomness for more realistic drafting
        if (Math.random() < 0.8) {
            return candidates[0]; // 80% chance to take the best option
        } else {
            return candidates[Math.floor(Math.random() * Math.min(3, candidates.length))];
        }
    }
    
    calculateTeamNeeds(roster) {
        const needs = [];
        
        // Check each position against limits
        if (roster.QB.length === 0) needs.push('QB');
        if (roster.RB.length < 2) needs.push('RB');
        if (roster.WR.length < 2) needs.push('WR');
        if (roster.TE.length === 0) needs.push('TE');
        
        // Secondary needs
        if (roster.QB.length < 2 && this.currentPick > 50) needs.push('QB');
        if (roster.RB.length < 4 && this.currentPick > 30) needs.push('RB');
        if (roster.WR.length < 4 && this.currentPick > 30) needs.push('WR');
        if (roster.TE.length < 2 && this.currentPick > 80) needs.push('TE');
        
        // Don't draft LB/DB too early
        if (this.currentPick > 90) {
            if (roster.LB.length < 2) needs.push('LB');
            if (roster.DB.length < 2) needs.push('DB');
        }
        
        return needs;
    }
    
    canDraftPosition(teamId, position) {
        const team = this.teams[teamId];
        const positionCount = team.roster[position].length;
        
        // Check position limits
        const limits = {
            QB: CONFIG.MAX_QB,
            RB: CONFIG.MAX_RB,
            WR: CONFIG.MAX_WR,
            TE: CONFIG.MAX_TE,
            LB: CONFIG.MAX_LB,
            DB: CONFIG.MAX_DB
        };
        
        return positionCount < (limits[position] || 10);
    }
    
    startTimer(callback) {
        this.currentTimer = this.timerSeconds;
        this.stopTimer();
        
        this.timerInterval = setInterval(() => {
            this.currentTimer--;
            
            if (callback) {
                callback(this.currentTimer);
            }
            
            if (this.currentTimer <= 0) {
                this.stopTimer();
                
                // Auto-pick if enabled
                if (this.autoPickEnabled) {
                    const pickInfo = this.getCurrentPickInfo();
                    if (!this.adminMode && !pickInfo.isUserPick) {
                        const computerPick = this.selectComputerPick();
                        if (computerPick) {
                            this.draftPlayer(computerPick);
                        }
                    }
                }
            }
        }, 1000);
    }
    
    stopTimer() {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
    }
    
    executeTrade(team1Id, pick1, team2Id, pick2) {
        this.trades.push({
            team1: team1Id,
            pick1: pick1,
            team2: team2Id,
            pick2: pick2
        });
        
        return true;
    }
    
    executeRoundTrade(team1Id, team1Rounds, team2Id, team2Rounds) {
        // Store trade by rounds (like the Python version)
        this.trades.push({
            team1: team1Id,
            team1Rounds: team1Rounds,
            team2: team2Id,
            team2Rounds: team2Rounds,
            type: 'rounds'
        });
        
        return true;
    }
    
    saveDraft(name) {
        const draftData = {
            name: name,
            date: new Date().toISOString(),
            teams: this.teams,
            draftHistory: this.draftHistory,
            trades: this.trades,
            userTeamId: this.userTeamId,
            currentPick: this.currentPick
        };
        
        const drafts = utils.loadFromStorage('savedDrafts') || [];
        drafts.push(draftData);
        utils.saveToStorage('savedDrafts', drafts);
        
        return true;
    }
    
    loadDraft(draftData) {
        this.teams = draftData.teams;
        this.draftHistory = draftData.draftHistory;
        this.trades = draftData.trades || [];
        this.userTeamId = draftData.userTeamId;
        this.currentPick = draftData.currentPick;
        
        // Rebuild drafted/available players lists
        this.availablePlayers = [...this.players];
        this.draftedPlayers = [];
        
        for (const pick of this.draftHistory) {
            const player = this.players.find(p => p.player_id === pick.player.player_id);
            if (player) {
                player.drafted = true;
                player.draftedBy = pick.player.draftedBy;
                player.draftedAt = pick.player.draftedAt;
                this.draftedPlayers.push(player);
                this.availablePlayers = this.availablePlayers.filter(
                    p => p.player_id !== player.player_id
                );
            }
        }
        
        return true;
    }
    
    restartDraft() {
        // Reset all players
        for (const player of this.players) {
            player.drafted = false;
            player.draftedBy = null;
            player.draftedAt = null;
        }
        
        // Reset teams
        this.initializeTeams();
        
        // Reset draft state
        this.currentPick = 1;
        this.draftHistory = [];
        this.trades = [];
        this.availablePlayers = [...this.players];
        this.availablePlayers.sort((a, b) => (a.adp || 999) - (b.adp || 999));
        
        return true;
    }
    
    async switchADPSource(usePrivate) {
        console.log('=== switchADPSource called ===');
        console.log('Switching to:', usePrivate ? 'PRIVATE' : 'PUBLIC');
        console.log('customADP entries:', Object.keys(this.customADP).length);
        console.log('customADP["8112"]:', this.customADP["8112"]);
        
        this.usePrivateADP = usePrivate;
        
        // Always use the same base player data
        const playersArray = this.privatePlayersData;
        
        if (!playersArray) {
            console.error('No player data available');
            return false;
        }
        
        // Preserve draft state
        const draftedInfo = {};
        for (const histItem of this.draftHistory) {
            draftedInfo[histItem.player.player_id] = histItem.player;
        }
        
        console.log(`Switching to ${usePrivate ? 'PRIVATE' : 'PUBLIC'} ADP mode`);
        
        // Reprocess player data with new ADP values
        this.players = playersArray.map(p => {
            const nameParts = (p.name || '').split(' ');
            const firstName = p.first_name || nameParts[0] || '';
            const lastName = p.last_name || nameParts.slice(1).join(' ') || '';
            const estimatedPoints = this.estimateFantasyPoints(p.position, p.adp || 999);
            
            // Store original ADP
            const originalADP = p.adp || 999;
            
            // Apply custom ADP ONLY for private mode
            let finalADP = originalADP;
            const customValue = this.customADP[p.player_id];
            if (usePrivate && customValue !== undefined) {
                finalADP = customValue;
                if (p.name === 'Drake London') {
                    console.log(`>>> APPLYING CUSTOM ADP: ${originalADP} -> ${customValue}`);
                }
            }
            
            // Debug Drake London specifically
            if (p.name && p.name.includes('Drake London')) {
                console.log('=== Drake London Debug ===');
                console.log('player_id:', p.player_id, 'type:', typeof p.player_id);
                console.log('usePrivate:', usePrivate);
                console.log('customADP["8112"]:', this.customADP["8112"]);
                console.log('customADP[p.player_id]:', this.customADP[p.player_id]);
                console.log('Condition (usePrivate && customADP[id]):', usePrivate && this.customADP[p.player_id]);
                console.log('Final ADP:', finalADP, '(should be', usePrivate ? '19.25' : '16', ')');
            }
            
            // Get real SOS from data
            const sosValue = this.sosData[p.team] ? this.sosData[p.team][p.position] : null;
            
            const player = {
                ...p,
                first_name: firstName,
                last_name: lastName,
                adp: finalADP,
                drafted: false,
                draftedBy: null,
                draftedAt: null,
                original_adp: originalADP,
                tier: p.tier || Math.ceil(finalADP / 12) || 1,
                sos: sosValue || p.sos || null, // Use real SOS data
                projected_rank: p.projected_rank || `${p.position}${Math.ceil(finalADP / CONFIG.NUM_TEAMS)}`,
                projected_points: p.projected_points || estimatedPoints,
                var: 0
            };
            
            // Restore draft state if this player was drafted
            if (draftedInfo[p.player_id]) {
                player.drafted = true;
                player.draftedBy = draftedInfo[p.player_id].draftedBy;
                player.draftedAt = draftedInfo[p.player_id].draftedAt;
            }
            
            return player;
        });
        
        // Sort by ADP
        this.players.sort((a, b) => (a.adp || 999) - (b.adp || 999));
        
        // Update available players
        this.availablePlayers = this.players.filter(p => !p.drafted);
        this.availablePlayers.sort((a, b) => (a.adp || 999) - (b.adp || 999));
        
        // Recalculate VAR
        this.calculateAllVAR();
        
        // Log first few players to verify
        const drakeLondon = this.players.find(p => p.name === 'Drake London');
        const drakeAvailable = this.availablePlayers.find(p => p.name === 'Drake London');
        
        console.log(`Mode: ${usePrivate ? 'PRIVATE' : 'PUBLIC'}`);
        console.log('Drake London in this.players:', drakeLondon ? {
            name: drakeLondon.name,
            player_id: drakeLondon.player_id,
            adp: drakeLondon.adp,
            original_adp: drakeLondon.original_adp
        } : 'NOT FOUND');
        console.log('Drake London in this.availablePlayers:', drakeAvailable ? {
            name: drakeAvailable.name,
            player_id: drakeAvailable.player_id,
            adp: drakeAvailable.adp,
            original_adp: drakeAvailable.original_adp
        } : 'NOT FOUND');
        console.log('Custom ADP for 8112:', this.customADP['8112']);
        
        return true;
    }
}

// Export for use in other modules
window.DraftManager = DraftManager;