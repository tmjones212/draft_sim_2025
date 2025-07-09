# Project: Mock Draft Simulator 2025

## How ADP (Average Draft Position) Works

### ADP Data Sources
1. **Primary source**: Local file `src/data/players_2025.json` (contains current ADP values)
2. **Fallback if local file missing**: Live ADP data from `https://nfc.shgn.com/adp.data.php`
3. **Custom overrides**: User-edited values saved in `data/custom_adp.json`

### ADP Loading Process
1. `generate_mock_players()` loads players via `get_players_with_fallback()`
2. Base ADP values come from the data source (local file or API)
3. When players are loaded in `main.py`:
   - `on_players_loaded()` applies custom ADP values BEFORE sorting
   - `available_players` is sorted by ADP (custom values take precedence)
4. Custom ADP values are also applied when:
   - Draft is restarted (`restart_draft`)
   - Draft spot is repicked (`repick_spot`)
   - Draft is reverted (`_revert_to_pick`)

### Critical: Available Players List Must Be Sorted
- **Issue**: Computer draft logic assumes `self.available_players` is sorted by ADP
- **Solution**: Always sort `available_players` by ADP when:
  - Players are initially loaded (`on_players_loaded`)
  - Draft is restarted (`restart_draft`, `repick_spot`)
  - Draft is reverted (`_revert_to_pick`)
  - Custom ADP values are changed (`on_adp_change`)
- **Sort key**: `lambda p: p.adp if p.adp else 999`

### Custom ADP Management
- Users can edit ADP by clicking on the ADP column in player list
- Custom values are saved to `data/custom_adp.json` 
- When ADP is edited, the `on_adp_change` callback re-sorts `available_players`
- Reset ADP button clears all custom values and restores defaults

### Computer Draft Logic
- `_select_computer_pick()` assumes `self.available_players[0]` has the best ADP
- Early picks (1-3) just take `available_players[0]`
- Later picks consider position needs but still rely on list order

## Important Reminders

### Always Sync to Windows
After making ANY changes, ALWAYS sync to Windows version:
```bash
./sync_to_windows.sh
```

MAKE SURE TO COMMIT WHEN YOU MAKE A CHANGE.

Windows local path: `C:\Users\alaba\source\repos\Python\draft_sim_2025`

**Important**: The sync script excludes `data/custom_adp.json` to preserve your custom ADP values on the Windows side.

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
- Added snap counts column showing offensive snaps per game (from 'off_snp' stat)
- Added Targets (Tgt) column positioned between Rush TD and Receptions
- Added sort direction arrows (↑/↓) to column headers showing current sort
- Added "Show Available" checkbox to filter out drafted players
- Moved week range controls and Clear Graph button above the graph for better UX

### Player List
- Team logos replace text (logos in assets/team_logos/)
- Right-click context menu for drafting
- Removed draft buttons from rows
- ADP header width increased to 55px
- Updated default sort directions: ascending first for Rank, CR, Pos, Name, Team, ADP, Proj Rank
- Proj Rank sorting now properly sorts by number first, then position (e.g., QB1, QB2, RB1)

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
- Added Targets (Tgt) column for RB/WR/TE positions
- Color thresholds for targets: RB (6+/≤3), WR (8+/≤4), TE (6+/≤3)

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
- Rank column sorting improved to sort by number first, then position (e.g., QB1 < QB2 < RB1)

- MAKE SURE YOU DON'T GET RID OF THE DB AND LB FILTER BUTTONS

### Defensive Players (LB/DB) Support (2025-07-06)
- LB and DB players are now loaded from data/players.json
- Added to fantasy_positions filter in player_data_fetcher.py
- Included in position rankings and VAR calculations
- VAR replacement levels: LB = 30th, DB = 30th (3 per team in 10-team league)
- Draft logic limits: Max 4 LBs and 4 DBs per team
- LB/DB players restricted from being drafted before round 10
- Position filters in UI already support LB/DB selection
- Game History tab shows defensive snaps (def_snp) for LB/DB players