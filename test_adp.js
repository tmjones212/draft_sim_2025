// Node.js test script to verify ADP logic
const fs = require('fs');

// Load the data files
const players2025 = JSON.parse(fs.readFileSync('web_app/data/players_2025.json', 'utf8'));
const customADP = JSON.parse(fs.readFileSync('web_app/data/custom_adp.json', 'utf8'));

const players = players2025.players || players2025;

// Find Drake London
const drakeLondon = players.find(p => p.name === 'Drake London');

console.log('Drake London base data:');
console.log('  Player ID:', drakeLondon.player_id);
console.log('  Base ADP:', drakeLondon.adp);
console.log('  Custom ADP:', customADP[drakeLondon.player_id]);

console.log('\nExpected behavior:');
console.log('  Public mode: ADP should be 16');
console.log('  Private mode: ADP should be 19.25');

// Simulate the logic
function simulateADP(usePrivate) {
    let finalADP = drakeLondon.adp || 999;
    if (usePrivate && customADP[drakeLondon.player_id]) {
        finalADP = customADP[drakeLondon.player_id];
    }
    return finalADP;
}

console.log('\nSimulated results:');
console.log('  Public mode:', simulateADP(false));
console.log('  Private mode:', simulateADP(true));