# Player List Synchronization Fixes

## Problem Summary
The available players table was getting out of sync after multiple picks and resets, showing:
1. Already drafted players in the top row
2. Misaligned columns (name shows one player, stats show another)
3. Unclickable rows
4. Wrong position data

## Root Causes
1. **Index-based operations** - Using array indices while the underlying data changes
2. **Row reuse without proper reset** - Hidden rows retained stale data when reused
3. **Player reference mismatch** - Row's player reference not updated when data changes
4. **Incomplete refresh during resets** - Partial updates left inconsistent state

## Key Fixes Applied

### 1. Player ID Tracking
Added player ID to row mapping for better tracking:
```python
# Add player ID to row mapping for better tracking
self.player_id_to_row: Dict[str, tk.Frame] = {}
```

### 2. Complete Table Refresh
Replaced smart update with complete refresh to avoid sync issues:
```python
def _complete_refresh_table(self):
    """Complete refresh of table - clears all rows and recreates them"""
    # Clear player ID mapping
    self.player_id_to_row.clear()
    
    # Hide all existing rows
    for row in self.row_frames:
        row.pack_forget()
        self.hidden_rows.append(row)
    self.row_frames.clear()
    
    # Clear any existing content
    for widget in self.table_frame.winfo_children():
        if not isinstance(widget, tk.Frame) or widget not in self.hidden_rows:
            widget.destroy()
```

### 3. Player ID-based Operations
Changed from index-based to player ID-based operations:
```python
def draft_specific_player(self, player: Player):
    """Draft a specific player object directly"""
    # Find the player's current index using player ID
    for i, p in enumerate(self.players):
        if p.player_id == player.player_id:
            self.select_player(i)
            if self.on_draft:
                self.on_draft()
            return
```

### 4. Row Content Reset
When reusing rows, completely clear and rebuild content:
```python
if self.hidden_rows:
    row = self.hidden_rows.pop()
    # Clear all existing content
    for widget in row.winfo_children():
        widget.destroy()
```

### 5. Player ID-based Selection
Updated row selection to use player IDs instead of object references:
```python
def select_row(self, index):
    """Highlight selected row"""
    self.selected_index = index
    selected_player = self.players[index] if index < len(self.players) else None
    
    for i, row in enumerate(self.row_frames):
        # Check if this row contains the selected player using player ID
        is_selected = hasattr(row, 'player') and row.player.player_id == selected_player.player_id
```

### 6. Simplified Remove Players
Use player IDs for efficient removal:
```python
def remove_players(self, players_to_remove: List[Player]):
    """Remove multiple players from the list efficiently"""
    if not players_to_remove:
        return
    
    # Create a set of player IDs for O(1) lookup
    player_ids_to_remove = {p.player_id for p in players_to_remove if p.player_id}
    
    # Remove from data
    self.players = [p for p in self.players if p.player_id not in player_ids_to_remove]
    
    # Force complete refresh to avoid sync issues
    self._complete_refresh_table()
```

## Implementation Instructions

1. **Backup the original file**:
   ```bash
   cp src/ui/player_list.py src/ui/player_list_backup.py
   ```

2. **Replace with the fixed version**:
   ```bash
   cp src/ui/player_list_fixed.py src/ui/player_list.py
   ```

3. **Test the fixes**:
   - Start a draft and make several picks
   - Use the reset button multiple times
   - Revert to earlier picks
   - Check that the player table stays in sync

4. **Sync to Windows** (as per project instructions):
   ```bash
   ./sync_to_windows.sh
   ```

## Additional Recommendations

1. **Consider using a virtual list** for better performance with large player lists
2. **Add data validation** to ensure player IDs are unique
3. **Implement unit tests** for the player list synchronization
4. **Add logging** to track table updates for debugging