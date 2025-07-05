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
- Position colors: QB (pink), RB (teal), WR (blue), TE (orange)

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

### Player Stats Popup Improvements
- Added completions column for QBs
- Color coding for good/bad performances (green/red)
- Position-specific thresholds for all stats
- Opponent shows @ or vs based on home/away

### Player List Changes
- Rank column now shows VAR rank instead of overall rank
- Default sort remains ADP (ascending)
