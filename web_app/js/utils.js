// Utility functions

// Format player name (matching Python's format_name)
function formatName(firstName, lastName) {
    if (!firstName && !lastName) return '';
    
    // Special cases
    const specialNames = {
        'Calvin': { 'Ridley': 'Ridley' },
        'Marvin': { 'Harrison': 'MHJ' },
        'Bijan': { 'Robinson': 'Bijan' },
        'Breece': { 'Hall': 'Breece' },
        'Jonathan': { 'Taylor': 'JT' },
        'Christian': { 'McCaffrey': 'CMC' },
        'Saquon': { 'Barkley': 'Saquon' },
        'Austin': { 'Ekeler': 'Ekeler' },
        'Davante': { 'Adams': 'Davante' },
        'Tyreek': { 'Hill': 'Tyreek' },
        'A.J.': { 'Brown': 'AJB' },
        'Stefon': { 'Diggs': 'Diggs' },
        'Justin': { 'Jefferson': 'JJ' },
        'CeeDee': { 'Lamb': 'CeeDee' },
        'Cooper': { 'Kupp': 'Kupp' },
        'Ja\'Marr': { 'Chase': 'Chase' },
        'Travis': { 'Kelce': 'Kelce' },
        'Mark': { 'Andrews': 'Mandrews' },
        'T.J.': { 'Hockenson': 'Hock' },
        'Kyle': { 'Pitts': 'Pitts' },
        'George': { 'Kittle': 'Kittle' },
        'Darren': { 'Waller': 'Waller' },
        'Dallas': { 'Goedert': 'Goedert' },
        'Patrick': { 'Mahomes': 'Mahomes' },
        'Josh': { 'Allen': 'JAllen' },
        'Jalen': { 'Hurts': 'Hurts' },
        'Lamar': { 'Jackson': 'Lamar' },
        'Joe': { 'Burrow': 'Burrow' },
        'Justin': { 'Herbert': 'Herbert' },
        'Trevor': { 'Lawrence': 'TLaw' },
        'Tua': { 'Tagovailoa': 'Tua' },
        'Dak': { 'Prescott': 'Dak' },
        'Russell': { 'Wilson': 'Russ' },
        'Aaron': { 'Rodgers': 'Rodgers' },
        'Kirk': { 'Cousins': 'Kirk' },
        'Matthew': { 'Stafford': 'Stafford' },
        'Derek': { 'Carr': 'Carr' },
        'Geno': { 'Smith': 'Geno' },
        'Daniel': { 'Jones': 'DJones' },
        'Mac': { 'Jones': 'Mac' },
        'Deshaun': { 'Watson': 'Watson' },
        'Kyler': { 'Murray': 'Kyler' },
        'Jared': { 'Goff': 'Goff' },
        'Brock': { 'Purdy': 'Purdy' },
        'C.J.': { 'Stroud': 'Stroud' },
        'Bryce': { 'Young': 'BYoung' },
        'Anthony': { 'Richardson': 'ARich' },
        'Will': { 'Levis': 'Levis' },
        'Jaylen': { 'Waddle': 'Waddle' },
        'DeVonta': { 'Smith': 'DSmith' },
        'DK': { 'Metcalf': 'DK' },
        'Mike': { 'Evans': 'Evans' },
        'Chris': { 'Olave': 'Olave' },
        'Amari': { 'Cooper': 'Cooper' },
        'DeAndre': { 'Hopkins': 'DHop' },
        'Keenan': { 'Allen': 'Keenan' },
        'Michael': { 'Pittman': 'Pittman' },
        'Calvin': { 'Ridley': 'Ridley' },
        'Terry': { 'McLaurin': 'Scary Terry' },
        'DJ': { 'Moore': 'DJ Moore' },
        'Marquise': { 'Brown': 'Hollywood' },
        'Jerry': { 'Jeudy': 'Jeudy' },
        'Brandon': { 'Aiyuk': 'Aiyuk' },
        'Deebo': { 'Samuel': 'Deebo' },
        'Amon-Ra': { 'St. Brown': 'ARSB' },
        'Garrett': { 'Wilson': 'GWilson' },
        'Chris': { 'Godwin': 'Godwin' },
        'Tyler': { 'Lockett': 'Lockett' },
        'Christian': { 'Watson': 'CWatson' },
        'Drake': { 'London': 'London' },
        'Treylon': { 'Burks': 'Burks' },
        'Jameson': { 'Williams': 'Jamo' },
        'George': { 'Pickens': 'Pickens' },
        'Rashod': { 'Bateman': 'Bateman' },
        'Elijah': { 'Moore': 'EMoore' },
        'Kadarius': { 'Toney': 'Toney' },
        'Jahan': { 'Dotson': 'Dotson' },
        'Skyy': { 'Moore': 'Skyy' },
        'Nick': { 'Chubb': 'Chubb' },
        'Derrick': { 'Henry': 'Henry' },
        'Josh': { 'Jacobs': 'Jacobs' },
        'Tony': { 'Pollard': 'Pollard' },
        'Rhamondre': { 'Stevenson': 'Rhamondre' },
        'Kenneth': { 'Walker': 'K9' },
        'Dameon': { 'Pierce': 'Pierce' },
        'Najee': { 'Harris': 'Najee' },
        'Aaron': { 'Jones': 'AJones' },
        'Miles': { 'Sanders': 'Sanders' },
        'Cam': { 'Akers': 'Akers' },
        'D\'Andre': { 'Swift': 'Swift' },
        'James': { 'Conner': 'Conner' },
        'Joe': { 'Mixon': 'Mixon' },
        'David': { 'Montgomery': 'Monty' },
        'Jamaal': { 'Williams': 'JWilliams' },
        'Alvin': { 'Kamara': 'Kamara' },
        'Leonard': { 'Fournette': 'Lenny' },
        'Ezekiel': { 'Elliott': 'Zeke' },
        'Dalvin': { 'Cook': 'Cook' },
        'James': { 'Cook': 'JCook' },
        'Rashaad': { 'Penny': 'Penny' },
        'Jeff': { 'Wilson': 'JWilson' },
        'Clyde': { 'Edwards-Helaire': 'CEH' },
        'AJ': { 'Dillon': 'Dillon' },
        'Kareem': { 'Hunt': 'Hunt' },
        'Samaje': { 'Perine': 'Perine' },
        'Rachaad': { 'White': 'White' },
        'Isiah': { 'Pacheco': 'Pacheco' },
        'Javonte': { 'Williams': 'Javonte' },
        'Michael': { 'Carter': 'MCarter' },
        'Jahmyr': { 'Gibbs': 'Gibbs' },
        'Devon': { 'Achane': 'Achane' },
        'Zach': { 'Charbonnet': 'Charb' },
        'Tank': { 'Bigsby': 'Tank' },
        'Roschon': { 'Johnson': 'Roschon' },
        'Tyjae': { 'Spears': 'Spears' },
        'Kendre': { 'Miller': 'KMiller' },
        'Israel': { 'Abanikanda': 'Izzy' },
        'Evan': { 'Engram': 'Engram' },
        'Darren': { 'Waller': 'Waller' },
        'Cole': { 'Kmet': 'Kmet' },
        'Pat': { 'Freiermuth': 'Muth' },
        'Tyler': { 'Higbee': 'Higbee' },
        'David': { 'Njoku': 'Njoku' },
        'Gerald': { 'Everett': 'Everett' },
        'Dalton': { 'Schultz': 'Schultz' },
        'Greg': { 'Dulcich': 'Dulcich' },
        'Juwan': { 'Johnson': 'JuwanJ' },
        'Chigoziem': { 'Okonkwo': 'Chig' },
        'Taysom': { 'Hill': 'Taysom' },
        'Sam': { 'LaPorta': 'LaPorta' },
        'Michael': { 'Mayer': 'Mayer' },
        'Luke': { 'Musgrave': 'Musgrave' },
        'Dalton': { 'Kincaid': 'Kincaid' },
        'Darnell': { 'Washington': 'DWash' }
    };
    
    if (specialNames[firstName] && specialNames[firstName][lastName]) {
        return specialNames[firstName][lastName];
    }
    
    // Default: FirstInitial.LastName
    if (firstName && lastName) {
        return `${firstName[0]}.${lastName}`;
    } else if (lastName) {
        return lastName;
    } else {
        return firstName;
    }
}

// Get team logo path
function getTeamLogo(team) {
    if (!team) return '';
    const teamLower = team.toLowerCase();
    return `team_logos/${teamLower}.png`;
}

// Get position color class
function getPositionClass(position) {
    return `pos-${position}`;
}

// Get tier color class
function getTierClass(tier) {
    return `tier-${tier}`;
}

// Get SOS color class
function getSOSClass(sos) {
    if (sos <= 10) return 'sos-easy';
    if (sos <= 20) return 'sos-medium';
    return 'sos-hard';
}

// Calculate draft order for snake draft with 3rd round reversal
function calculateDraftOrder(numTeams, numRounds) {
    const draftOrder = [];
    
    for (let round = 1; round <= numRounds; round++) {
        const roundPicks = [];
        
        if (round === 1) {
            // Round 1: Normal order
            for (let pick = 1; pick <= numTeams; pick++) {
                roundPicks.push(pick);
            }
        } else if (round === 2) {
            // Round 2: Reverse order
            for (let pick = numTeams; pick >= 1; pick--) {
                roundPicks.push(pick);
            }
        } else if (round === 3 && CONFIG.THIRD_ROUND_REVERSAL) {
            // Round 3: Same as round 2 (3rd round reversal)
            for (let pick = numTeams; pick >= 1; pick--) {
                roundPicks.push(pick);
            }
        } else {
            // Subsequent rounds: Alternate based on previous round
            const prevRound = draftOrder[round - 2];
            if (prevRound[0] === 1) {
                // Previous was normal, so reverse
                for (let pick = numTeams; pick >= 1; pick--) {
                    roundPicks.push(pick);
                }
            } else {
                // Previous was reversed, so normal
                for (let pick = 1; pick <= numTeams; pick++) {
                    roundPicks.push(pick);
                }
            }
        }
        
        draftOrder.push(roundPicks);
    }
    
    return draftOrder;
}

// Get pick number from round and position
function getPickNumber(round, position, numTeams) {
    return (round - 1) * numTeams + position;
}

// Get round and position from pick number
function getRoundAndPosition(pickNumber, numTeams) {
    const round = Math.ceil(pickNumber / numTeams);
    const position = ((pickNumber - 1) % numTeams) + 1;
    return { round, position };
}

// Save to localStorage
function saveToStorage(key, data) {
    try {
        localStorage.setItem(key, JSON.stringify(data));
        return true;
    } catch (e) {
        console.error('Failed to save to localStorage:', e);
        return false;
    }
}

// Load from localStorage
function loadFromStorage(key) {
    try {
        const data = localStorage.getItem(key);
        return data ? JSON.parse(data) : null;
    } catch (e) {
        console.error('Failed to load from localStorage:', e);
        return null;
    }
}

// Delete from localStorage
function deleteFromStorage(key) {
    try {
        localStorage.removeItem(key);
        return true;
    } catch (e) {
        console.error('Failed to delete from localStorage:', e);
        return false;
    }
}

// Format time (seconds to MM:SS)
function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Shuffle array (for randomizing computer picks with some variance)
function shuffleArray(array) {
    const shuffled = [...array];
    for (let i = shuffled.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    return shuffled;
}

// Deep clone object
function deepClone(obj) {
    return JSON.parse(JSON.stringify(obj));
}

// Debounce function for search inputs
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Calculate Value Above Replacement (VAR)
function calculateVAR(player, playersByPosition) {
    const position = player.position;
    const replacementLevel = CONFIG.VAR_LEVELS[position] || 30;
    
    const positionPlayers = playersByPosition[position] || [];
    const replacementPlayer = positionPlayers[replacementLevel - 1];
    
    if (!replacementPlayer) {
        return 0;
    }
    
    const playerValue = player.projected_points || 0;
    const replacementValue = replacementPlayer.projected_points || 0;
    
    return Math.round(playerValue - replacementValue);
}

// Parse projected rank (e.g., "RB5" -> {position: "RB", rank: 5})
function parseProjectedRank(projRank) {
    if (!projRank) return null;
    
    const match = projRank.match(/^([A-Z]+)(\d+)$/);
    if (!match) return null;
    
    return {
        position: match[1],
        rank: parseInt(match[2])
    };
}

// Generate unique ID
function generateId() {
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
}

// Check if player matches position filter
function matchesPositionFilter(player, filter) {
    if (filter === 'ALL') return true;
    if (filter === 'FLEX') {
        return ['RB', 'WR', 'TE'].includes(player.position);
    }
    return player.position === filter;
}

// Export functions for use in other modules
window.utils = {
    formatName,
    getTeamLogo,
    getPositionClass,
    getTierClass,
    getSOSClass,
    calculateDraftOrder,
    getPickNumber,
    getRoundAndPosition,
    saveToStorage,
    loadFromStorage,
    deleteFromStorage,
    formatTime,
    shuffleArray,
    deepClone,
    debounce,
    calculateVAR,
    parseProjectedRank,
    generateId,
    matchesPositionFilter
};