// Main Application Module

let draftManager;
let currentTab = 'draft';
let selectedPlayers = new Set(); // For game history graph

// Define updateDraftBoard at global scope before anything else
function updateDraftBoard() {
    if (!draftManager) return;
    
    const container = document.getElementById('draftBoard');
    const visibleRounds = parseInt(document.getElementById('visibleRounds').value) || 3;
    
    container.innerHTML = '';
    
    for (let round = 1; round <= Math.min(visibleRounds, CONFIG.NUM_ROUNDS); round++) {
        const roundDiv = document.createElement('div');
        roundDiv.className = 'draft-round';
        
        const roundHeader = document.createElement('h4');
        roundHeader.textContent = `Round ${round}`;
        roundDiv.appendChild(roundHeader);
        
        const picksDiv = document.createElement('div');
        picksDiv.className = 'draft-picks';
        
        // Determine if we need to reverse the display order for snake draft
        let positions = [];
        for (let pos = 1; pos <= CONFIG.NUM_TEAMS; pos++) {
            positions.push(pos);
        }
        
        // For snake draft visual display, show picks in the order they happen
        const needsReversal = (round === 2) || (round === 3 && CONFIG.THIRD_ROUND_REVERSAL) || 
                             (round > 3 && round % 2 === 1);
        
        if (needsReversal) {
            positions.reverse();
        }
        
        for (let pos of positions) {
            const pickNum = utils.getPickNumber(round, pos, CONFIG.NUM_TEAMS);
            const teamId = draftManager.getTeamAtPosition(round, pos) - 1;
            const team = draftManager.teams[teamId];
            
            const pickDiv = document.createElement('div');
            pickDiv.className = 'draft-pick';
            
            // Check if this pick has been made
            const draftedPick = draftManager.draftHistory.find(h => h.pick === pickNum);
            
            if (draftedPick) {
                pickDiv.innerHTML = `
                    <div class="pick-number">#${pickNum}</div>
                    <div class="pick-team">${team.name}</div>
                    <div class="pick-player ${utils.getPositionClass(draftedPick.player.position)}">
                        ${utils.formatName(draftedPick.player.first_name, draftedPick.player.last_name)}
                    </div>
                `;
                
                // Add click handler to revert to this pick
                pickDiv.style.cursor = 'pointer';
                pickDiv.addEventListener('click', () => {
                    if (confirm(`Revert draft to pick #${pickNum}?`)) {
                        revertToPick(pickNum);
                    }
                });
            } else {
                pickDiv.innerHTML = `
                    <div class="pick-number">#${pickNum}</div>
                    <div class="pick-team">${team.name}</div>
                    <div class="pick-player">-</div>
                `;
            }
            
            // Highlight current pick
            if (pickNum === draftManager.currentPick) {
                pickDiv.classList.add('current');
            }
            
            // Highlight user's picks
            if (teamId === draftManager.userTeamId) {
                pickDiv.classList.add('user-pick');
            }
            
            // Show traded picks
            const trade = draftManager.trades.find(t => 
                t.pick1 === pickNum || t.pick2 === pickNum
            );
            if (trade) {
                pickDiv.classList.add('traded');
            }
            
            picksDiv.appendChild(pickDiv);
        }
        
        roundDiv.appendChild(picksDiv);
        container.appendChild(roundDiv);
    }
}

// Make it globally accessible
window.updateDraftBoard = updateDraftBoard;

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', async function initApp() {
    // Initialize draft manager
    draftManager = new DraftManager();
    window.draftManager = draftManager; // Make it globally accessible
    
    // Always start with public ADP (don't load saved preference)
    // const savedADPPreference = utils.loadFromStorage('usePrivateADP');
    // if (savedADPPreference) {
    //     draftManager.usePrivateADP = true;
    // }
    
    // Load players data
    const loaded = await draftManager.loadPlayers();
    if (!loaded) {
        alert('Failed to load player data. Please refresh the page.');
        return;
    }
    
    // Update ADP button text based on loaded state
    const adpBtn = document.getElementById('adpToggleBtn');
    if (draftManager.usePrivateADP) {
        adpBtn.textContent = 'ADP: Private';
        adpBtn.classList.remove('btn-secondary');
        adpBtn.classList.add('btn-primary');
    }
    
    // Setup UI event handlers
    setupEventHandlers();
    
    // Setup tab navigation
    setupTabNavigation();
    
    // Initialize UI first
    updateDraftBoard();
    updatePlayerList();
    
    // Show draft spot modal to let user choose their team
    setTimeout(() => {
        showDraftSpotModal();
    }, 500);
});

function setupEventHandlers() {
    // Header buttons
    document.getElementById('restartBtn').addEventListener('click', restartDraft);
    document.getElementById('repickSpotBtn').addEventListener('click', () => {
        console.log('Repick spot button clicked');
        showDraftSpotModal();
    });
    document.getElementById('undoBtn').addEventListener('click', undoLastPick);
    document.getElementById('adpToggleBtn').addEventListener('click', toggleADPSource);
    document.getElementById('settingsBtn').addEventListener('click', showSettingsModal);
    
    // Player list controls
    document.getElementById('playerSearch').addEventListener('input', 
        utils.debounce(() => updatePlayerList(), 300)
    );
    document.getElementById('positionFilter').addEventListener('change', updatePlayerList);
    document.getElementById('resetAdpBtn').addEventListener('click', resetADP);
    
    // Player table sorting
    document.querySelectorAll('#playerTable th[data-sort]').forEach(th => {
        th.addEventListener('click', () => sortPlayerTable(th.dataset.sort));
    });
    
    // Draft board controls
    document.getElementById('visibleRounds').addEventListener('change', updateDraftBoard);
    
    // Settings modal
    document.getElementById('saveSettingsBtn').addEventListener('click', saveSettings);
    document.getElementById('cancelSettingsBtn').addEventListener('click', hideSettingsModal);
    
    // Manager notes modal
    document.getElementById('closeNotesBtn').addEventListener('click', hideManagerNotesModal);
}

function setupTabNavigation() {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const tabName = btn.dataset.tab;
            switchTab(tabName);
        });
    });
}

// Track which tabs have been initialized
const initializedTabs = new Set();

function switchTab(tabName) {
    // Update active tab button
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });
    
    // Update active tab pane
    document.querySelectorAll('.tab-pane').forEach(pane => {
        pane.classList.toggle('active', pane.id === `${tabName}-tab`);
    });
    
    currentTab = tabName;
    
    // Initialize tab-specific content only once
    if (!initializedTabs.has(tabName)) {
        initializedTabs.add(tabName);
        
        if (tabName === 'game-history') {
            initializeGameHistory();
        } else if (tabName === 'prev-drafts') {
            initializePrevDrafts();
        } else if (tabName === 'trade') {
            initializeTrade();
        }
    }
}

function showDraftSpotModal() {
    const modal = document.getElementById('draftSpotModal');
    const grid = document.getElementById('draftSpotGrid');
    
    if (!modal || !grid) {
        console.error('Draft spot modal elements not found, using fallback');
        // Fallback: Use a simple prompt
        const teams = CONFIG.TEAM_NAMES.map((name, i) => `${i+1}. ${name}`).join('\n');
        const choice = prompt(`Select your draft position (1-10):\n\n${teams}\n\nEnter number (1-10):`);
        if (choice) {
            const teamId = parseInt(choice) - 1;
            if (teamId >= 0 && teamId < CONFIG.NUM_TEAMS) {
                selectDraftSpot(teamId);
            }
        }
        return;
    }
    
    // Clear existing buttons
    grid.innerHTML = '';
    
    // Create draft spot buttons
    for (let i = 0; i < CONFIG.NUM_TEAMS; i++) {
        const btn = document.createElement('button');
        btn.className = 'draft-spot-btn';
        btn.textContent = `${i + 1}. ${CONFIG.TEAM_NAMES[i]}`;
        btn.addEventListener('click', ((teamIndex) => {
            return (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log(`Selected draft spot: ${teamIndex} - ${CONFIG.TEAM_NAMES[teamIndex]}`);
                hideDraftSpotModal(); // Hide modal first
                setTimeout(() => {
                    selectDraftSpot(teamIndex); // Then select the spot
                }, 100);
            };
        })(i)); // Use closure to capture the correct index
        grid.appendChild(btn);
    }
    
    modal.classList.add('active');
    modal.style.display = 'flex'; // Force display
    console.log('Draft spot modal shown', modal, modal.classList);
}

function hideDraftSpotModal() {
    const modal = document.getElementById('draftSpotModal');
    if (modal) {
        modal.classList.remove('active');
        modal.style.display = 'none'; // Force hide
    }
}

function selectDraftSpot(teamId) {
    console.log(`selectDraftSpot called with teamId: ${teamId}`);
    
    try {
        if (!draftManager) {
            console.error('Draft manager not initialized');
            alert('Error: Draft not initialized. Please refresh the page.');
            return;
        }
        
        draftManager.userTeamId = teamId;
        console.log(`User team set to: ${CONFIG.TEAM_NAMES[teamId]}`);
        
        // Hide the modal first
        hideDraftSpotModal();
        
        // Update the UI
        updateDraftBoard();
        updateCurrentPick();
        
        // Start computer drafting if not user's pick
        setTimeout(() => {
            console.log('Starting computer picks...');
            processComputerPicks();
        }, 500); // Small delay to let the UI update first
        
    } catch (error) {
        console.error('Error in selectDraftSpot:', error);
        alert(`Error selecting draft spot: ${error.message}`);
    }
}


function updatePlayerList() {
    const tbody = document.getElementById('playerTableBody');
    const searchTerm = document.getElementById('playerSearch').value.toLowerCase();
    const positionFilter = document.getElementById('positionFilter').value;
    
    tbody.innerHTML = '';
    
    // Filter players
    let filteredPlayers = draftManager.availablePlayers.filter(player => {
        const matchesSearch = !searchTerm || 
            player.first_name.toLowerCase().includes(searchTerm) ||
            player.last_name.toLowerCase().includes(searchTerm) ||
            player.team.toLowerCase().includes(searchTerm);
        
        const matchesPosition = utils.matchesPositionFilter(player, positionFilter);
        
        return matchesSearch && matchesPosition;
    });
    
    // Create table rows
    filteredPlayers.forEach(player => {
        const row = document.createElement('tr');
        
        // VAR Rank
        const varCell = document.createElement('td');
        varCell.textContent = player.var || '-';
        row.appendChild(varCell);
        
        // Custom Rank (Tier)
        const tierCell = document.createElement('td');
        tierCell.className = utils.getTierClass(player.tier);
        tierCell.textContent = player.tier || '-';
        row.appendChild(tierCell);
        
        // Position
        const posCell = document.createElement('td');
        posCell.className = utils.getPositionClass(player.position);
        posCell.textContent = player.position;
        row.appendChild(posCell);
        
        // Name
        const nameCell = document.createElement('td');
        nameCell.textContent = utils.formatName(player.first_name, player.last_name);
        row.appendChild(nameCell);
        
        // Team
        const teamCell = document.createElement('td');
        const teamLogo = document.createElement('img');
        teamLogo.src = utils.getTeamLogo(player.team);
        teamLogo.className = 'team-logo';
        teamLogo.alt = player.team;
        teamCell.appendChild(teamLogo);
        row.appendChild(teamCell);
        
        // ADP (editable)
        const adpCell = document.createElement('td');
        adpCell.textContent = Math.round(player.adp) || '-';
        adpCell.style.cursor = 'pointer';
        adpCell.addEventListener('click', () => editADP(player, adpCell));
        row.appendChild(adpCell);
        
        // SOS
        const sosCell = document.createElement('td');
        sosCell.className = utils.getSOSClass(player.sos);
        sosCell.textContent = player.sos || '-';
        row.appendChild(sosCell);
        
        // Projected Rank
        const projCell = document.createElement('td');
        projCell.textContent = player.projected_rank || '-';
        row.appendChild(projCell);
        
        // Action
        const actionCell = document.createElement('td');
        const draftBtn = document.createElement('button');
        draftBtn.className = 'btn btn-small btn-primary';
        draftBtn.textContent = 'Draft';
        draftBtn.addEventListener('click', () => draftPlayerAction(player));
        actionCell.appendChild(draftBtn);
        row.appendChild(actionCell);
        
        // Add row select functionality
        row.addEventListener('click', (e) => {
            if (e.target.tagName !== 'BUTTON' && e.target.tagName !== 'TD') return;
            
            // Remove previous selection
            tbody.querySelectorAll('tr').forEach(r => r.classList.remove('selected'));
            row.classList.add('selected');
        });
        
        // Add double-click to draft
        row.addEventListener('dblclick', (e) => {
            e.preventDefault();
            draftPlayerAction(player);
        });
        
        // Add right-click context menu
        row.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            draftPlayerAction(player);
        });
        
        tbody.appendChild(row);
    });
}

function editADP(player, cell) {
    const currentValue = Math.round(player.adp) || '';
    const input = document.createElement('input');
    input.type = 'number';
    input.value = currentValue;
    input.style.width = '50px';
    input.style.padding = '2px';
    input.style.background = 'var(--bg-tertiary)';
    input.style.color = 'var(--text-primary)';
    input.style.border = '1px solid var(--border-color)';
    
    const saveEdit = () => {
        const newValue = parseInt(input.value);
        if (newValue && newValue > 0 && newValue <= 500) {
            draftManager.updatePlayerADP(player.player_id, newValue);
            updatePlayerList();
        } else {
            cell.textContent = currentValue;
        }
    };
    
    input.addEventListener('blur', saveEdit);
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            saveEdit();
        }
    });
    
    cell.innerHTML = '';
    cell.appendChild(input);
    input.focus();
    input.select();
}

function resetADP() {
    if (confirm('Are you sure you want to reset all custom ADP values?')) {
        draftManager.resetAllADP();
        updatePlayerList();
    }
}

function sortPlayerTable(column) {
    const tbody = document.getElementById('playerTableBody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const th = document.querySelector(`#playerTable th[data-sort="${column}"]`);
    
    // Determine sort direction
    const isAscending = th.classList.contains('sort-desc');
    
    // Update header indicators
    document.querySelectorAll('#playerTable th').forEach(header => {
        header.classList.remove('sort-asc', 'sort-desc');
        header.textContent = header.textContent.replace(' ↑', '').replace(' ↓', '');
    });
    
    if (isAscending) {
        th.classList.add('sort-asc');
        th.textContent += ' ↑';
    } else {
        th.classList.add('sort-desc');
        th.textContent += ' ↓';
    }
    
    // Sort the filtered players
    let sortedPlayers = [...draftManager.availablePlayers];
    
    switch (column) {
        case 'rank':
            sortedPlayers.sort((a, b) => isAscending ? 
                (a.var || 999) - (b.var || 999) : 
                (b.var || 0) - (a.var || 0)
            );
            break;
        case 'tier':
            sortedPlayers.sort((a, b) => isAscending ? 
                (a.tier || 999) - (b.tier || 999) : 
                (b.tier || 0) - (a.tier || 0)
            );
            break;
        case 'position':
            sortedPlayers.sort((a, b) => isAscending ? 
                a.position.localeCompare(b.position) : 
                b.position.localeCompare(a.position)
            );
            break;
        case 'name':
            sortedPlayers.sort((a, b) => {
                const nameA = utils.formatName(a.first_name, a.last_name);
                const nameB = utils.formatName(b.first_name, b.last_name);
                return isAscending ? nameA.localeCompare(nameB) : nameB.localeCompare(nameA);
            });
            break;
        case 'team':
            sortedPlayers.sort((a, b) => isAscending ? 
                a.team.localeCompare(b.team) : 
                b.team.localeCompare(a.team)
            );
            break;
        case 'adp':
            sortedPlayers.sort((a, b) => isAscending ? 
                (a.adp || 999) - (b.adp || 999) : 
                (b.adp || 999) - (a.adp || 999)
            );
            break;
        case 'sos':
            sortedPlayers.sort((a, b) => isAscending ? 
                (a.sos || 999) - (b.sos || 999) : 
                (b.sos || 999) - (a.sos || 999)
            );
            break;
        case 'projRank':
            sortedPlayers.sort((a, b) => {
                const rankA = utils.parseProjectedRank(a.projected_rank);
                const rankB = utils.parseProjectedRank(b.projected_rank);
                
                if (!rankA && !rankB) return 0;
                if (!rankA) return 1;
                if (!rankB) return -1;
                
                if (rankA.rank !== rankB.rank) {
                    return isAscending ? rankA.rank - rankB.rank : rankB.rank - rankA.rank;
                }
                
                return isAscending ? 
                    rankA.position.localeCompare(rankB.position) : 
                    rankB.position.localeCompare(rankA.position);
            });
            break;
    }
    
    draftManager.availablePlayers = sortedPlayers;
    updatePlayerList();
}

function draftPlayerAction(player) {
    const pickInfo = draftManager.getCurrentPickInfo();
    
    // Check if it's the user's turn or admin mode
    if (!draftManager.adminMode && !pickInfo.isUserPick) {
        alert('It\'s not your turn to pick!');
        return;
    }
    
    // Check position limits
    if (!draftManager.canDraftPosition(pickInfo.team.id, player.position)) {
        alert(`Cannot draft another ${player.position}. Position limit reached.`);
        return;
    }
    
    // Draft the player
    if (draftManager.draftPlayer(player)) {
        updateDraftBoard();
        updatePlayerList();
        updateCurrentPick();
        
        // Process computer picks
        processComputerPicks();
    }
}

function processComputerPicks() {
    const pickInfo = draftManager.getCurrentPickInfo();
    
    // If draft is complete
    if (draftManager.currentPick > CONFIG.NUM_TEAMS * CONFIG.NUM_ROUNDS) {
        alert('Draft complete!');
        return;
    }
    
    // If it's the user's pick or admin mode, don't auto-pick
    if (pickInfo.isUserPick || draftManager.adminMode) {
        return;
    }
    
    // Make computer pick after a very short delay (just for visual feedback)
    setTimeout(() => {
        const computerPick = draftManager.selectComputerPick();
        if (computerPick) {
            draftManager.draftPlayer(computerPick);
            updateDraftBoard();
            updatePlayerList();
            updateCurrentPick();
            
            // Continue processing if next pick is also computer
            processComputerPicks();
        }
    }, 100); // Reduced from 1000ms to 100ms for much faster drafting
}

function updateCurrentPick() {
    const pickInfo = draftManager.getCurrentPickInfo();
    const display = document.getElementById('currentPickDisplay');
    
    if (draftManager.currentPick > CONFIG.NUM_TEAMS * CONFIG.NUM_ROUNDS) {
        display.innerHTML = '<strong>Draft Complete!</strong>';
        return;
    }
    
    display.innerHTML = `
        <strong>Pick ${pickInfo.pickNumber}</strong> - 
        Round ${pickInfo.round}, Pick ${pickInfo.position}<br>
        <strong>${pickInfo.team.name}</strong> is on the clock
    `;
}

function undoLastPick() {
    if (draftManager.undoLastPick()) {
        updateDraftBoard();
        updatePlayerList();
        updateCurrentPick();
        
        // After undoing, process computer picks if needed
        processComputerPicks();
    } else {
        alert('No picks to undo.');
    }
}

function revertToPick(targetPick) {
    // Undo picks until we reach the target pick
    while (draftManager.currentPick > targetPick && draftManager.draftHistory.length > 0) {
        if (!draftManager.undoLastPick()) {
            break;
        }
    }
    
    updateDraftBoard();
    updatePlayerList();
    updateCurrentPick();
    
    // After reverting, process computer picks if needed
    processComputerPicks();
}

function restartDraft() {
    if (confirm('Are you sure you want to restart the draft? All picks will be lost.')) {
        draftManager.restartDraft();
        updateDraftBoard();
        updatePlayerList();
        showDraftSpotModal();
    }
}

function showSettingsModal() {
    const modal = document.getElementById('settingsModal');
    
    // Load current settings
    document.getElementById('soundEnabled').checked = false; // Not implemented yet
    document.getElementById('adminMode').checked = draftManager.adminMode;
    
    modal.classList.add('active');
}

function hideSettingsModal() {
    document.getElementById('settingsModal').classList.remove('active');
}

function saveSettings() {
    draftManager.adminMode = document.getElementById('adminMode').checked;
    
    // Save to localStorage
    utils.saveToStorage('draftSettings', {
        adminMode: draftManager.adminMode
    });
    
    hideSettingsModal();
}

function showManagerNotesModal() {
    const modal = document.getElementById('managerNotesModal');
    const list = document.getElementById('managerNotesList');
    
    // Load manager notes
    const notes = utils.loadFromStorage('managerNotes') || {};
    
    list.innerHTML = '';
    
    CONFIG.TEAM_NAMES.forEach(name => {
        const noteDiv = document.createElement('div');
        noteDiv.className = 'manager-note-item';
        
        const header = document.createElement('h4');
        header.textContent = name;
        noteDiv.appendChild(header);
        
        const textarea = document.createElement('textarea');
        textarea.value = notes[name] || '';
        textarea.placeholder = 'Enter draft habits and notes...';
        textarea.addEventListener('change', () => {
            notes[name] = textarea.value;
            utils.saveToStorage('managerNotes', notes);
        });
        noteDiv.appendChild(textarea);
        
        list.appendChild(noteDiv);
    });
    
    modal.classList.add('active');
}

function hideManagerNotesModal() {
    document.getElementById('managerNotesModal').classList.remove('active');
}

// ADP Toggle Function
function toggleADPSource() {
    const btn = document.getElementById('adpToggleBtn');
    const currentlyPrivate = draftManager.usePrivateADP;
    
    if (!currentlyPrivate) {
        // Switching to private - require password
        const password = prompt('Enter password to access private ADP:');
        
        // Check password
        if (password !== 'xyz') {
            alert('Incorrect password!');
            return;
        }
    }
    
    // Switch the ADP source
    draftManager.switchADPSource(!currentlyPrivate).then(success => {
        if (success) {
            btn.textContent = draftManager.usePrivateADP ? 'ADP: Private' : 'ADP: Public';
            btn.classList.toggle('btn-primary', draftManager.usePrivateADP);
            btn.classList.toggle('btn-secondary', !draftManager.usePrivateADP);
            
            // Update the player list with new data
            updatePlayerList();
            
            // Don't save the state to localStorage
            // utils.saveToStorage('usePrivateADP', draftManager.usePrivateADP);
        } else {
            alert('Failed to switch ADP source. Private data may not be loaded.');
        }
    });
}

// Initialize other tabs
function initializeGameHistory() {
    // Implementation will be in gameHistory.js
    if (window.initGameHistory) {
        window.initGameHistory();
    }
}

function initializePrevDrafts() {
    const select = document.getElementById('draftSelect');
    const drafts = utils.loadFromStorage('savedDrafts') || [];
    
    select.innerHTML = '';
    drafts.forEach((draft, index) => {
        const option = document.createElement('option');
        option.value = index;
        option.textContent = `${draft.name} - ${new Date(draft.date).toLocaleDateString()}`;
        select.appendChild(option);
    });
    
    document.getElementById('loadDraftBtn').addEventListener('click', () => {
        const index = parseInt(select.value);
        if (!isNaN(index) && drafts[index]) {
            draftManager.loadDraft(drafts[index]);
            updateDraftBoard();
            updatePlayerList();
            switchTab('draft');
        }
    });
    
    document.getElementById('deleteDraftBtn').addEventListener('click', () => {
        const index = parseInt(select.value);
        if (!isNaN(index) && drafts[index]) {
            if (confirm(`Delete draft "${drafts[index].name}"?`)) {
                drafts.splice(index, 1);
                utils.saveToStorage('savedDrafts', drafts);
                initializePrevDrafts();
            }
        }
    });
    
    document.getElementById('managerNotesBtn').addEventListener('click', showManagerNotesModal);
}

function initializeTrade() {
    // Implementation will be in trade.js
    if (window.initTrade) {
        window.initTrade();
    }
}