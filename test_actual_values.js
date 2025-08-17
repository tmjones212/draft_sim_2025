// Direct test of actual values in files
const fs = require('fs');
const path = require('path');

console.log('=== CHECKING ACTUAL FILE VALUES ===\n');

// Check web_app data files
const webPlayers = JSON.parse(fs.readFileSync('web_app/data/players_2025.json', 'utf8'));
const webCustomADP = JSON.parse(fs.readFileSync('web_app/data/custom_adp.json', 'utf8'));

const players = webPlayers.players || webPlayers;
const drakeLondon = players.find(p => p.name === 'Drake London');

console.log('web_app/data/players_2025.json:');
console.log('  Drake London player_id:', drakeLondon?.player_id);
console.log('  Drake London base ADP:', drakeLondon?.adp);

console.log('\nweb_app/data/custom_adp.json:');
console.log('  Custom ADP for player 8112:', webCustomADP['8112']);

// Check Windows/tkinter data files
try {
    const winPlayers = JSON.parse(fs.readFileSync('/mnt/c/Users/alaba/source/repos/Python/draft_sim_2025/src/data/players_2025.json', 'utf8'));
    const winCustomADP = JSON.parse(fs.readFileSync('/mnt/c/Users/alaba/source/repos/Python/draft_sim_2025/data/custom_adp.json', 'utf8'));
    
    const winPlayersArray = winPlayers.players || winPlayers;
    const winDrake = winPlayersArray.find(p => p.name === 'Drake London');
    
    console.log('\n=== WINDOWS/TKINTER FILES ===');
    console.log('src/data/players_2025.json:');
    console.log('  Drake London player_id:', winDrake?.player_id);
    console.log('  Drake London base ADP:', winDrake?.adp);
    
    console.log('\ndata/custom_adp.json:');
    console.log('  Custom ADP for player 8112:', winCustomADP['8112']);
} catch (e) {
    console.log('\nCould not read Windows files:', e.message);
}

console.log('\n=== EXPECTED BEHAVIOR ===');
console.log('Public mode: Drake London should show ADP', drakeLondon?.adp);
console.log('Private mode: Drake London should show ADP', webCustomADP['8112'] || drakeLondon?.adp);