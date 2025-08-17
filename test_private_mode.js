// Test if custom ADP is being applied correctly
const fs = require('fs');

// Load the files
const customADP = JSON.parse(fs.readFileSync('web_app/data/custom_adp.json', 'utf8'));
const players2025 = JSON.parse(fs.readFileSync('web_app/data/players_2025.json', 'utf8'));

const players = players2025.players || players2025;
const drakeLondon = players.find(p => p.name === 'Drake London');

console.log('=== Drake London Data ===');
console.log('Player ID:', drakeLondon.player_id);
console.log('Base ADP:', drakeLondon.adp);
console.log('');

console.log('=== Custom ADP Data ===');
console.log('Custom ADP for 8112:', customADP['8112']);
console.log('Type of player_id:', typeof drakeLondon.player_id);
console.log('Type of customADP key:', typeof Object.keys(customADP)[0]);
console.log('');

// Test the condition
const usePrivate = true;
const condition = usePrivate && customADP[drakeLondon.player_id];

console.log('=== Condition Test ===');
console.log('usePrivate:', usePrivate);
console.log('customADP[drakeLondon.player_id]:', customADP[drakeLondon.player_id]);
console.log('Condition result:', condition);
console.log('');

// Check if the key exists
console.log('=== Key Check ===');
console.log('Does key "8112" exist?:', '8112' in customADP);
console.log('Does key 8112 exist?:', 8112 in customADP);
console.log('customADP["8112"]:', customADP["8112"]);
console.log('customADP[8112]:', customADP[8112]);