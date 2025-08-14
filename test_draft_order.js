// Test the draft order logic
function calculateDraftOrder() {
  const numTeams = 10;
  const rounds = 6; // Test first 6 rounds
  const draftOrder = [];
  
  for (let round = 1; round <= rounds; round++) {
    const order = [];
    for (let i = 1; i <= numTeams; i++) {
      order.push(i);
    }
    
    // Snake draft with 3rd round reversal
    // Rounds 1, 3, 5, 7, ... go 1-10
    // Rounds 2, 4, 6, 8, ... go 10-1
    // The pattern is: Normal, Reverse, Normal, Reverse starting from round 3
    if (round === 2) {
      // Round 2 is reversed
      order.reverse();
    } else if (round >= 3) {
      // From round 3 onwards: odd rounds normal, even rounds reversed
      if (round % 2 === 0) {
        order.reverse();
      }
    }
    
    draftOrder.push(...order);
  }
  
  return draftOrder;
}

// Test and display results
const draftOrder = calculateDraftOrder();
const rounds = 6;
const numTeams = 10;

console.log("Draft Order with 3rd Round Reversal:");
console.log("=====================================");

for (let round = 1; round <= rounds; round++) {
  const startIdx = (round - 1) * numTeams;
  const endIdx = startIdx + numTeams;
  const roundOrder = draftOrder.slice(startIdx, endIdx);
  console.log(`Round ${round}: ${roundOrder.join(', ')}`);
}

console.log("\nKey picks for Team 1 (1.01 owner):");
const team1Picks = [];
for (let i = 0; i < draftOrder.length; i++) {
  if (draftOrder[i] === 1) {
    const round = Math.floor(i / 10) + 1;
    const pick = (i % 10) + 1;
    team1Picks.push(`${round}.${pick.toString().padStart(2, '0')}`);
  }
}
console.log(team1Picks.join(', '));

console.log("\nExpected for Team 1: 1.01, 2.10, 3.01, 4.10, 5.01, 6.10");
console.log("Correct? " + (team1Picks.join(', ') === "1.01, 2.10, 3.01, 4.10, 5.01, 6.10" ? "✓ YES" : "✗ NO"));