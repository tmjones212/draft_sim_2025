import json
from collections import Counter, defaultdict

# Load ADP data
with open("data/adp_data.json", "r") as f:
    adp_data = json.load(f)

print("=== ADP ANALYSIS ===")
print(f"Total players with ADP: {len(adp_data)}")
print()

# Create list of (name, adp) tuples and sort by ADP
adp_list = [(name, float(adp)) for name, adp in adp_data.items()]
adp_list.sort(key=lambda x: x[1])

# 1. Check for duplicate ADPs
adp_values = [x[1] for x in adp_list]
adp_counts = Counter(adp_values)
duplicates = [(adp, count) for adp, count in adp_counts.items() if count > 1]

print("ISSUE 1: Duplicate ADPs")
print(f"Found {len(duplicates)} ADPs assigned to multiple players:")
for adp, count in sorted(duplicates)[:20]:
    players_at_adp = [name for name, a in adp_list if a == adp]
    print(f"  ADP {adp}: {count} players - {', '.join(players_at_adp[:3])}")
    if len(players_at_adp) > 3:
        print(f"    ... and {len(players_at_adp) - 3} more")
print()

# 2. Check ADP distribution by round (12-team league)
print("ISSUE 2: Players per round (12-team league, should be exactly 12):")
issues_found = False
for round_num in range(1, 16):
    start = (round_num - 1) * 12 + 1
    end = round_num * 12
    players_in_round = [x for x in adp_list if start <= x[1] <= end]
    if len(players_in_round) != 12:
        status = "TOO MANY!" if len(players_in_round) > 12 else "too few"
        print(f"  Round {round_num} (picks {start}-{end}): {len(players_in_round)} players ({status})")
        issues_found = True
if not issues_found:
    print("  All rounds have exactly 12 players - OK!")
print()

# 3. Check for unrealistic ADP ranges
print("ISSUE 3: ADP Distribution (looking for overcrowding):")
ranges = [(1, 10), (11, 20), (21, 30), (31, 40), (41, 50), (51, 60), (61, 70), (71, 80), (81, 90), (91, 100)]
for start, end in ranges:
    count = len([x for x in adp_list if start <= x[1] <= end])
    expected = end - start + 1
    if count > expected:
        print(f"  ADP {start}-{end}: {count} players (expected max {expected}) - OVERCROWDED!")
    elif count < expected * 0.7:
        print(f"  ADP {start}-{end}: {count} players (expected ~{expected}) - sparse")
print()

# 4. Find specific issues like you mentioned
print("ISSUE 4: Checking for logical impossibilities:")
top_10 = [x for x in adp_list if x[1] <= 10]
print(f"  Players with ADP 1-10: {len(top_10)} (should be exactly 10)")
if len(top_10) > 10:
    print("  Players:")
    for name, adp in top_10:
        print(f"    {name}: {adp}")
print()

# 5. Check for gaps
print("ISSUE 5: Large gaps in ADP sequence:")
gaps = []
for i in range(1, len(adp_list)):
    gap = adp_list[i][1] - adp_list[i-1][1]
    if gap > 5:
        gaps.append((adp_list[i-1], adp_list[i], gap))
print(f"Found {len(gaps)} large gaps (> 5.0)")
for (name1, adp1), (name2, adp2), gap in gaps[:10]:
    print(f"  Gap of {gap:.1f} between {name1} (ADP {adp1}) and {name2} (ADP {adp2})")
print()

# 6. Position analysis for early rounds
print("ISSUE 6: Position distribution in early rounds:")
# Load players to get positions
with open("data/players.json", "r") as f:
    players = json.load(f)

# Create name to position mapping
name_to_pos = {p["name"]: p["position"] for p in players}

# Analyze positions by round
for round_num in range(1, 6):
    start = (round_num - 1) * 12 + 1
    end = round_num * 12
    players_in_round = [(name, adp) for name, adp in adp_list if start <= adp <= end]
    pos_counts = Counter([name_to_pos.get(name, "Unknown") for name, _ in players_in_round])
    print(f"  Round {round_num}: {dict(pos_counts)}")