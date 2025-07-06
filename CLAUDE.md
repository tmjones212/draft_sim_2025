# Project: Mock Draft Simulator 2025

## Important Reminders

### Always Sync to Windows
After making ANY changes, ALWAYS sync to Windows version:
```bash
./sync_to_windows.sh
```

MAKE SURE TO COMMIT WHEN YOU MAKE A CHANGE.

Windows local path: `C:\Users\alaba\source\repos\Python\draft_sim_2025`

### Misc
Also use the formatted player name (the format_name function in player_extensions.py)

### Draft Logic
- Snake draft with 3rd round reversal (rounds 2 and 3 go the same direction)
- Configuration in `config.py`

### UI Requirements
- Dark theme matching Sleeper's draft board style
- Position colors: QB (pink), RB (teal), WR (blue), TE (orange), DB (light purple), LB (light pink)

### Running the App
- Linux: `python3 main.py`
- Windows: Double-click `run_windows.bat`

When you learn useful things that would be helpful in the future, memorialize them in CLAUDE.md

## Recent UI Improvements (2025-07-05)

### Game History Tab
- Position filter now only shows main positions (ALL, QB, RB, WR, TE, FLEX)
- Columns dynamically show/hide based on position filter
- Added summarized/detailed view toggle
- Fixed Rush TD calculation to prevent negative numbers
- Added snap counts column showing offensive snaps per game (from 'off_snp' stat)

### Player List
- Team logos replace text (logos in assets/team_logos/)
- Right-click context menu for drafting
- Removed draft buttons from rows
- ADP header width increased to 55px

### Draft Board
- Default visible rounds reduced to 3
- Sash position adjusted to 45% for more player list space

### Global UI
- Reduced header padding for more vertical space
- Removed global Enter/Space keybindings that interfered with search

### Custom ADP Persistence
- Added CustomADPManager to save/load custom ADP values
- Custom ADP values are saved to data/custom_adp.json
- Values persist between app sessions
- Added "Reset ADP" button to clear all custom values
- Custom values are automatically applied when players are loaded

### Player List Updates
- ADP displays as integers (not decimals)
- Single left-click to edit ADP values
- Default sort changed to ADP (ascending)

### Game History Improvements
- Added completions column for QBs
- Fixed QB scoring to use custom scoring (0.5 pts/completion, etc.)
- Custom scoring calculation: Completions × 0.5, Pass Yards × 0.05, Rush Yards × 0.2, Receptions × 2.0, Rec Yards × 0.2, All TDs × 6.0
- Bonuses: 300+ pass yards = +6, 100+ rush/rec yards = +3
- Dynamic column visibility based on position filter
- Added Location filter (ALL/HOME/AWAY)
- Added Venue filter (ALL/DOME/OUTSIDE)
- Dome teams: ATL, DET, MIN, NO, LV, ARI, DAL, HOU, IND
- Opponent column shows @ for away games, vs for home games
- Uses ttk.Treeview for performance (no logos in table, but fast loading)
- Added snaps column showing offensive snap counts (after points column)
- Added Pts/Snap column showing efficiency metric (3 decimal places)
- Added Rank column showing positional rank for week (e.g., WR1, RB12, QB7)
- First click on columns sorts descending for better stats viewing
- Default sort is Points (descending) to show highest scoring games first

### Player Stats Popup Improvements
- Added completions column for QBs
- Color coding for good/bad performances (green/red)
- Position-specific thresholds for all stats
- Opponent shows @ or vs based on home/away

### Player List Changes
- Rank column now shows VAR rank instead of overall rank
- Default sort remains ADP (ascending)

### Game History Data Loading (2025-07-05)
- Fixed duplicate game counting issue
- Now loads from aggregated_player_stats_2024.json file first
- Falls back to individual week files in stats_data/ directory if needed
- Ensures only one entry per player per week
- Handles both single stat objects and lists of stats for compatibility
- Added auto-resize columns functionality that adjusts column widths based on content after filtering
- Added totals row when filtering by single player showing sum of all stats and averages
- Added points-by-week graph panel on the right side of game history table
- Click on any player to graph their weekly points
- Ctrl+Click to add/remove multiple players (toggle functionality)
- Shift+Click to select all players between last clicked and current
- Shows 0 points for bye/injury weeks instead of skipping them
- Graph legend shows standard deviation (σ) for each player (excluding weeks with <5 snaps)
- Graph uses team colors for better distinction between players
- Different marker shapes (circle, square, triangle, etc.) for multiple players from same team
- Clear Graph button to reset the visualization
- Y-axis always starts at 0 for consistent scale
- Week range selector with presets: All, First Half, Last Half, Q1-Q4, Playoffs
- Custom week range using spinboxes for any weeks 1-18

## DB and LB Positions Added (2025-07-05)

### Draft Configuration
- Added DB and LB roster spots (2 each) to config.py
- Updated roster view to display DB and LB positions

### UI Updates
- Added DB and LB to position filters in Player List and Game History
- Added position colors: DB (light purple #9966ff), LB (light pink #ff66cc)
- Position buttons now include DB and LB options

### Data Processing
- Updated pull_stats.py and pull_projections.py to fetch DB and LB data
- Added DB and LB to VAR calculations with replacement levels of 20 each
- Added defensive scoring in scoring.py (tackles, sacks, interceptions, etc.)

### Draft Logic
- Computer teams draft DB and LB positions with max of 2 each
- DB and LB are treated as late-round positions (after round 10)
- Added to position counts tracking for draft strategy

### Scoring Configuration for IDP
- Tackle: 1.0 point
- Tackle Assist: 0.5 points
- Sack: 2.0 points
- Interception: 6.0 points
- Pass Deflection: 1.0 point
- Forced Fumble: 3.0 points
- Fumble Recovery: 3.0 points
- Defensive TD: 6.0 points
- Safety: 2.0 points

### DB/LB Player Fixes (2025-07-06)
- Fixed issue where clicking on one DB/LB player would highlight all DB/LB players
  - Problem: DB/LB players in players_2025.json don't have player_id fields
  - Solution: Updated player_list.py to use object identity comparison when player_id is missing
- Fixed DB/LB players not showing in game history
  - Added 'db' and 'lb' to positions loaded in game_history.py
  - Added IDP scoring calculation for DB/LB players
  - Updated table rows to show defensive stats (tackles, sacks, ints) for DB/LB
  - Use defensive snaps (def_snp) instead of offensive snaps for DB/LB players
