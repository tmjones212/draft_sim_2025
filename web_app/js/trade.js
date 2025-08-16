// Trade Module

let tradeInitialized = false;

window.initTrade = function() {
    // Prevent multiple initialization
    if (tradeInitialized) return;
    tradeInitialized = true;
    
    console.log('Initializing trade tab, draftManager:', window.draftManager);
    
    const team1Select = document.getElementById('team1Select');
    const team2Select = document.getElementById('team2Select');
    const team1PickSelect = document.getElementById('team1PickSelect');
    const team2PickSelect = document.getElementById('team2PickSelect');
    
    // Add preset trade button (only if it doesn't exist)
    const tradeForm = document.querySelector('.trade-form');
    if (!document.getElementById('presetTradeBtn')) {
        const presetBtn = document.createElement('button');
        presetBtn.id = 'presetTradeBtn';
        presetBtn.className = 'btn btn-secondary';
        presetBtn.textContent = 'Load Preset Trade (8,38,63 ⇄ 14,24,77)';
        presetBtn.style.marginBottom = '20px';
        presetBtn.addEventListener('click', (e) => {
            e.preventDefault();
            loadPresetTrade();
        });
        tradeForm.parentNode.insertBefore(presetBtn, tradeForm);
    }
    
    // Populate team dropdowns
    CONFIG.TEAM_NAMES.forEach((name, index) => {
        const option1 = document.createElement('option');
        option1.value = index;
        option1.textContent = name;
        team1Select.appendChild(option1);
        
        const option2 = document.createElement('option');
        option2.value = index;
        option2.textContent = name;
        team2Select.appendChild(option2);
    });
    
    // Populate pick dropdowns
    for (let round = 1; round <= CONFIG.NUM_ROUNDS; round++) {
        for (let pos = 1; pos <= CONFIG.NUM_TEAMS; pos++) {
            const pickNum = utils.getPickNumber(round, pos, CONFIG.NUM_TEAMS);
            
            const option1 = document.createElement('option');
            option1.value = pickNum;
            option1.textContent = `Pick ${pickNum} (Round ${round})`;
            team1PickSelect.appendChild(option1);
            
            const option2 = document.createElement('option');
            option2.value = pickNum;
            option2.textContent = `Pick ${pickNum} (Round ${round})`;
            team2PickSelect.appendChild(option2);
        }
    }
    
    // Execute trade button
    document.getElementById('executeTradeBtn').addEventListener('click', () => {
        const team1 = parseInt(team1Select.value);
        const team2 = parseInt(team2Select.value);
        const pick1 = parseInt(team1PickSelect.value);
        const pick2 = parseInt(team2PickSelect.value);
        
        if (team1 === team2) {
            alert('Cannot trade with the same team.');
            return;
        }
        
        if (pick1 === pick2) {
            alert('Cannot trade the same pick.');
            return;
        }
        
        if (draftManager.executeTrade(team1, pick1, team2, pick2)) {
            alert(`Trade executed: ${CONFIG.TEAM_NAMES[team1]} Pick ${pick1} for ${CONFIG.TEAM_NAMES[team2]} Pick ${pick2}`);
            
            // Update trade history
            const historyDiv = document.getElementById('tradeHistory');
            const tradeDiv = document.createElement('div');
            tradeDiv.innerHTML = `
                <strong>Trade:</strong> ${CONFIG.TEAM_NAMES[team1]} sends Pick ${pick1} to ${CONFIG.TEAM_NAMES[team2]} 
                for Pick ${pick2}
            `;
            historyDiv.appendChild(tradeDiv);
            
            // Update draft board
            if (window.draftManager) {
                updateDraftBoard();
            }
        }
    });
    
    // Function to load the preset trade
    function loadPresetTrade() {
        console.log('Loading preset trade, draftManager:', window.draftManager);
        
        // Check both local and global draftManager
        const dm = window.draftManager || draftManager;
        
        if (dm && dm.teams) {
            // Clear any existing trades first
            dm.trades = [];
            
            // Execute the trade: ME (index 7) trades rounds 1,4,7 to PAT (index 6) for rounds 2,3,8
            // ME gives up picks 8,38,63 and gets PAT's picks 14,24,77
            dm.executeRoundTrade(7, [1, 4, 7], 6, [2, 3, 8]);
            
            console.log('Trade added:', dm.trades);
            
            // Update trade history
            const historyDiv = document.getElementById('tradeHistory');
            historyDiv.innerHTML = ''; // Clear existing
            const tradeDiv = document.createElement('div');
            tradeDiv.innerHTML = '<strong>Preset Trade Active:</strong><br>' +
                                 'ME trades: R1 (#8), R4 (#38), R7 (#63)<br>' +
                                 'PAT trades: R2 (#14), R3 (#24), R8 (#77)<br>' +
                                 'Result: ME gets PAT\'s picks 14,24,77 and PAT gets ME\'s picks 8,38,63';
            historyDiv.appendChild(tradeDiv);
            
            // Force update draft board
            if (typeof updateDraftBoard === 'function') {
                updateDraftBoard();
            } else if (window.updateDraftBoard) {
                window.updateDraftBoard();
            }
            
            alert('Preset trade loaded!\nME gets PAT\'s picks: 14, 24, 77\nPAT gets ME\'s picks: 8, 38, 63');
        } else {
            console.error('Draft manager not found or not initialized:', dm);
            alert('Error: Draft not properly initialized. Please refresh the page and try again.');
        }
    }
};