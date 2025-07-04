import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Optional, Callable
from ..models import Player
from .theme import DARK_THEME, get_position_color
from .styled_widgets import StyledFrame


class PlayerList(StyledFrame):
    def __init__(self, parent, on_select: Optional[Callable] = None, on_draft: Optional[Callable] = None, image_service=None, **kwargs):
        super().__init__(parent, bg_type='secondary', **kwargs)
        self.on_select = on_select
        self.on_draft = on_draft
        self.players: List[Player] = []
        self.selected_index = None
        self.image_cache = {}  # Cache loaded images
        self.player_cards = []
        self.draft_enabled = False
        self.image_service = image_service
        self.all_players: List[Player] = []  # Store all players
        self.selected_position = "ALL"  # Current filter
        self.sort_by = "rank"  # Default sort by rank
        self.sort_ascending = True  # Track sort direction
        self.dragging_player = None  # Track dragged player
        self.drag_window = None  # Drag preview window
        self.watched_player_ids = set()  # Track watched players
        self.watch_list_ref = None  # Reference to watch list widget
        self.drag_start_pos = None  # Track drag start position
        self.is_dragging = False  # Track if actually dragging
        self.setup_ui()
        
    def setup_ui(self):
        # Main container
        container = StyledFrame(self, bg_type='secondary')
        container.pack(fill='both', expand=True)
        
        # Header with title and search
        header_frame = StyledFrame(container, bg_type='secondary')
        header_frame.pack(fill='x', pady=(0, 10))
        
        title = tk.Label(
            header_frame,
            text="AVAILABLE PLAYERS",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 11, 'bold')
        )
        title.pack(side='left')
        
        # Search box
        search_frame = StyledFrame(header_frame, bg_type='secondary')
        search_frame.pack(side='left', padx=20)
        
        search_label = tk.Label(
            search_frame,
            text="Search:",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 9)
        )
        search_label.pack(side='left', padx=(0, 5))
        
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(
            search_frame,
            textvariable=self.search_var,
            bg=DARK_THEME['bg_tertiary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10),
            width=20
        )
        self.search_entry.pack(side='left')
        self.search_var.trace('w', lambda *args: self.on_search_changed())
        
        # Position filter buttons
        filter_frame = StyledFrame(header_frame, bg_type='secondary')
        filter_frame.pack(side='left', padx=20)
        
        # Add position filter buttons
        positions = ["ALL", "QB", "RB", "WR", "TE", "FLEX"]
        self.position_buttons = {}
        
        for pos in positions:
            # Use position colors for filter buttons
            if pos == "ALL":
                btn_bg = DARK_THEME['button_active']
            elif pos == "FLEX":
                btn_bg = DARK_THEME['button_active'] if pos == self.selected_position else DARK_THEME['button_bg']
            elif pos in ["QB", "RB", "WR", "TE"]:
                btn_bg = get_position_color(pos) if pos == self.selected_position else DARK_THEME['button_bg']
            else:
                btn_bg = DARK_THEME['button_bg']
            
            btn = tk.Button(
                filter_frame,
                text=pos,
                bg=btn_bg,
                fg='white',
                font=(DARK_THEME['font_family'], 9, 'bold'),
                bd=0,
                relief='flat',
                padx=12,
                pady=4,
                command=lambda p=pos: self.filter_by_position(p),
                cursor='hand2',
                activebackground=btn_bg
            )
            btn.pack(side='left', padx=1)
            self.position_buttons[pos] = btn
        
        # Table container
        self.create_table_view(container)
    
    def create_table_view(self, parent):
        """Create the table view for players"""
        self.table_container = StyledFrame(parent, bg_type='secondary')
        self.table_container.pack(fill='both', expand=True)
        
        # Header with darker background and border
        header_border = tk.Frame(self.table_container, bg=DARK_THEME['border'], height=37)
        header_border.pack(fill='x', padx=10, pady=(10, 0))
        
        header_container = tk.Frame(header_border, bg=DARK_THEME['bg_tertiary'], height=35)
        header_container.pack(fill='both', expand=True, padx=1, pady=1)
        header_container.pack_propagate(False)
        
        # Store header labels for updating sort indicators
        self.header_labels = {}
        
        # Column headers with exact pixel widths matching the cells
        headers = [
            ('Rank', 50, 'rank'),
            ('', 25, None),      # Star column
            ('Pos', 45, None),
            ('Name', 180, None),
            ('Team', 45, None),
            ('ADP', 45, 'adp'),
            ('GP', 40, 'games_2024'),  # Added 5px
            ('2024 Pts', 75, 'points_2024'),  # Added 10px
            ('Proj Rank', 85, 'position_rank_proj'),  # Added 10px
            ('Proj Pts', 75, 'points_2025_proj'),  # Added 10px
            ('VAR', 60, 'var'),  # Added 10px
            ('', 80, None)       # Draft button
        ]
        
        for text, width, sort_key in headers:
            header_frame = tk.Frame(header_container, bg=DARK_THEME['bg_tertiary'], width=width)
            header_frame.pack(side='left', fill='y')
            header_frame.pack_propagate(False)
            
            # Add sort indicator to default sort column
            display_text = text
            if sort_key == 'rank' and not hasattr(self, '_sort_initialized'):
                display_text = text + ' ▲'  # Default sort by rank ascending
                self._sort_initialized = True
                
            header = tk.Label(
                header_frame,
                text=display_text,
                bg=DARK_THEME['bg_tertiary'],
                fg='white',
                font=(DARK_THEME['font_family'], 12, 'bold'),
                anchor='center' if text != 'Name' else 'w',
                cursor='hand2' if sort_key else 'arrow'
            )
            header.pack(expand=True)
            
            # Store header labels for sortable columns
            if sort_key:
                self.header_labels[sort_key] = (header, text)
                header.bind('<Button-1>', lambda e, key=sort_key: self.sort_players(key))
        
        # Scrollable content
        content_container = StyledFrame(self.table_container, bg_type='secondary')
        content_container.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        # Canvas for scrolling
        self.canvas = tk.Canvas(
            content_container, 
            bg=DARK_THEME['bg_secondary'], 
            highlightthickness=0,
            height=400
        )
        scrollbar = tk.Scrollbar(content_container, orient='vertical', command=self.canvas.yview)
        
        self.table_frame = tk.Frame(self.canvas, bg=DARK_THEME['bg_secondary'])
        self.table_frame.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        
        self.canvas_window = self.canvas.create_window((0, 0), window=self.table_frame, anchor='nw')
        
        # Make table frame expand to canvas width
        def configure_canvas(event):
            canvas_width = event.width
            self.canvas.itemconfig(self.canvas_window, width=canvas_width)
        
        self.canvas.bind('<Configure>', configure_canvas)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Mouse wheel scrolling - bind to all child widgets
        def on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), 'units')
            
        self.canvas.bind('<MouseWheel>', on_mousewheel)
        self.table_frame.bind('<MouseWheel>', on_mousewheel)
        
        # Bind mousewheel to all children as they're created
        self._mousewheel_handler = on_mousewheel
        
        # Store row frames
        self.row_frames = []
        self.selected_row = None
        self.hidden_rows = []  # Pool of hidden rows to reuse
    
    def update_players(self, players: List[Player], limit: int = 30):
        # Store all players
        self.all_players = players
        
        # Apply position filter
        if self.selected_position == "ALL":
            filtered_players = players
        elif self.selected_position == "FLEX":
            # FLEX shows RB, WR, and TE
            filtered_players = [p for p in players if p.position in ["RB", "WR", "TE"]]
        else:
            filtered_players = [p for p in players if p.position == self.selected_position]
        
        # Apply sorting - use attrgetter for better performance
        if self.sort_by == "rank":
            filtered_players.sort(key=lambda p: p.rank, reverse=not self.sort_ascending)
        elif self.sort_by == "adp":
            filtered_players.sort(key=lambda p: p.adp if p.adp else float('inf'), reverse=not self.sort_ascending)
        elif self.sort_by == "games_2024":
            filtered_players.sort(key=lambda p: getattr(p, 'games_2024', 0) or 0, reverse=not self.sort_ascending)
        elif self.sort_by == "points_2024":
            filtered_players.sort(key=lambda p: getattr(p, 'points_2024', 0) or 0, reverse=not self.sort_ascending)
        elif self.sort_by == "points_2025_proj":
            filtered_players.sort(key=lambda p: getattr(p, 'points_2025_proj', 0) or 0, reverse=not self.sort_ascending)
        elif self.sort_by == "var":
            filtered_players.sort(key=lambda p: getattr(p, 'var', -100) if getattr(p, 'var', None) is not None else -100, reverse=not self.sort_ascending)
        else:
            filtered_players.sort(key=lambda p: p.rank, reverse=not self.sort_ascending)
        
        self.players = filtered_players
        self.selected_index = None
        
        # Always update table view
        self.update_table_view()
    
    def remove_player_card(self, index: int):
        """Remove a specific player without refreshing all players"""
        if 0 <= index < len(self.players) and 0 <= index < len(self.row_frames):
            # Get the player and row
            player = self.players[index]
            
            # Find the actual row that contains this player
            row_to_remove = None
            row_index = None
            for i, row in enumerate(self.row_frames):
                if hasattr(row, 'player') and row.player == player:
                    row_to_remove = row
                    row_index = i
                    break
            
            if row_to_remove is None:
                return  # Player not found in rows
            
            # Remove from data
            self.players.pop(index)
            
            # Remove the row
            row_to_remove.pack_forget()
            self.row_frames.pop(row_index)
            self.hidden_rows.append(row_to_remove)
            
            # Update indices and colors for remaining rows
            for i in range(row_index, len(self.row_frames)):
                self.row_frames[i].index = i
                bg = DARK_THEME['bg_tertiary'] if i % 2 == 0 else DARK_THEME['bg_secondary']
                self._update_row_background(self.row_frames[i], bg)
    
    def _update_row_background(self, row, bg):
        """Update background color for a row and all its children"""
        row.configure(bg=bg)
        
        # Update all child widgets
        for widget in row.winfo_children():
            if isinstance(widget, tk.Frame):
                widget.configure(bg=bg)
                for child in widget.winfo_children():
                    if hasattr(child, 'configure'):
                        try:
                            if hasattr(child, '_is_star_button'):
                                # Star button special handling
                                child.configure(bg=bg, activebackground=bg)
                            elif not isinstance(child, tk.Button):
                                child.configure(bg=bg)
                        except:
                            pass
            elif isinstance(widget, tk.Label):
                try:
                    widget.configure(bg=bg)
                except:
                    pass
    
    def _update_row_colors(self, start_index):
        """Update alternating row colors starting from given index"""
        for i in range(start_index, len(self.row_frames)):
            row = self.row_frames[i]
            bg = DARK_THEME['bg_tertiary'] if i % 2 == 0 else DARK_THEME['bg_secondary']
            self._update_row_background(row, bg)
    
    def remove_players(self, players_to_remove: List[Player]):
        """Remove multiple players from the list efficiently"""
        if not players_to_remove:
            return
        
        import time
        method_start = time.time()
        
        # Create a set for O(1) lookup
        players_to_remove_set = set(players_to_remove)
        
        # Find which rows to remove
        rows_to_remove = []
        for i, row in enumerate(self.row_frames):
            if hasattr(row, 'player') and row.player in players_to_remove_set:
                rows_to_remove.append((i, row))
        
        # Remove from data
        self.players = [p for p in self.players if p not in players_to_remove_set]
        
        # Smoothly slide up the remaining rows
        if rows_to_remove:
            # First, mark rows for removal with a fade effect
            for idx, row in rows_to_remove:
                row.pack_forget()
                
            # Remove from our list
            for idx, row in sorted(rows_to_remove, reverse=True):
                self.row_frames.remove(row)
                self.hidden_rows.append(row)
            
            # Update indices and colors for remaining rows
            for i, row in enumerate(self.row_frames):
                row.index = i
                # Update background color
                bg = DARK_THEME['bg_tertiary'] if i % 2 == 0 else DARK_THEME['bg_secondary']
                self._update_row_background(row, bg)
        
        print(f"  [remove_players] Removed {len(rows_to_remove)} players in {time.time()-method_start:.3f}s")
    
    def _update_row_background(self, row, bg):
        """Update background color of a row and all its children"""
        row.configure(bg=bg)
        
        # Update all child widgets
        for widget in row.winfo_children():
            if isinstance(widget, tk.Frame):
                # Don't change button frames or position badges
                has_button = any(isinstance(child, tk.Button) for child in widget.winfo_children())
                has_position = any(isinstance(child, tk.Frame) and child.cget('bg') in ['#FF5E5B', '#23CDCD', '#5E9BFF', '#FF8C42'] for child in widget.winfo_children())
                
                if not has_button and not has_position:
                    widget.configure(bg=bg)
                    # Update label children
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Label) and not has_position:
                            child.configure(bg=bg)
            elif isinstance(widget, tk.Label):
                widget.configure(bg=bg)
    
    def select_player(self, index: int):
        """Select a player by index"""
        if index >= len(self.players):
            return
            
        self.selected_index = index
        
        # Callback
        if self.on_select:
            self.on_select(self.players[index])
    
    def get_selected_player(self) -> Optional[Player]:
        if self.selected_index is not None and self.selected_index < len(self.players):
            return self.players[self.selected_index]
        return None
    
    def draft_player(self, index: int):
        """Draft a specific player by index"""
        self.select_player(index)
        if self.on_draft:
            self.on_draft()
    
    def draft_specific_player(self, player: Player):
        """Draft a specific player object directly"""
        # Find the player's current index
        for i, p in enumerate(self.players):
            if p == player:
                self.select_player(i)
                if self.on_draft:
                    self.on_draft()
                return
        # Player not found - might have been drafted already
        return
    
    def filter_by_position(self, position: str):
        """Filter players by position"""
        self.selected_position = position
        
        # Update button appearances with position colors
        for pos, btn in self.position_buttons.items():
            if pos == position:
                if pos == "ALL" or pos == "FLEX":
                    btn.config(bg=DARK_THEME['button_active'], activebackground=DARK_THEME['button_active'])
                else:
                    pos_color = get_position_color(pos)
                    btn.config(bg=pos_color, activebackground=pos_color)
            else:
                btn.config(bg=DARK_THEME['button_bg'], activebackground=DARK_THEME['button_bg'])
        
        # Refresh the player list with the filter applied
        self.update_players(self.all_players)
    
    def sort_players(self, sort_by: str):
        """Sort players by specified criteria"""
        # Toggle sort direction if clicking the same column
        if self.sort_by == sort_by:
            self.sort_ascending = not self.sort_ascending
        else:
            # New column - default to descending for stats, ascending for rank/adp
            self.sort_by = sort_by
            if sort_by in ['games_2024', 'points_2024', 'points_2025_proj']:
                self.sort_ascending = False  # Descending by default for stats
            else:
                self.sort_ascending = True  # Ascending by default for rank/adp
        
        # Update header indicators
        self.update_sort_indicators()
        
        # Refresh the player list with the new sort
        self.update_players(self.all_players)
    
    def update_sort_indicators(self):
        """Update sort arrows on column headers"""
        if hasattr(self, 'header_labels'):
            for sort_key, (label, base_text) in self.header_labels.items():
                if sort_key == self.sort_by:
                    # Add appropriate arrow
                    arrow = ' ▲' if self.sort_ascending else ' ▼'
                    label.config(text=base_text + arrow)
                else:
                    # Remove arrow
                    label.config(text=base_text)
    
    def set_draft_enabled(self, enabled: bool):
        """Enable or disable all draft buttons"""
        self.draft_enabled = enabled
    
    def update_table_view(self):
        """Update the table view with current players"""
        # If we're just filtering/sorting, try to do a smart update
        if hasattr(self, '_initialized') and self._initialized:
            self._smart_update_table()
            return
        
        # First time initialization
        self._initialized = True
        
        # Limit display to first 100 players for performance
        max_display = min(100, len(self.players))
        
        # Create all rows at once
        for i in range(max_display):
            self.create_player_row(i, self.players[i])
        
        # If there are more players, show a message
        if len(self.players) > max_display:
            more_label = tk.Label(
                self.table_frame,
                text=f"... and {len(self.players) - max_display} more players. Use search to find specific players.",
                bg=DARK_THEME['bg_secondary'],
                fg=DARK_THEME['text_secondary'],
                font=(DARK_THEME['font_family'], 10, 'italic')
            )
            more_label.pack(pady=10)
        
        # Update canvas scroll region after adding all rows
        self.table_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
    
    def _smart_update_table(self):
        """Smart update that reuses existing rows when possible"""
        max_display = min(100, len(self.players))
        current_row_count = len(self.row_frames)
        
        # Don't do batch updates - update rows immediately for smoother experience
        # Just update the data in existing rows without clearing
        
        # Update existing rows
        for i in range(min(current_row_count, max_display)):
            self.update_player_row(self.row_frames[i], i, self.players[i])
        
        # Hide extra rows if we have fewer players
        if current_row_count > max_display:
            for i in range(max_display, current_row_count):
                row = self.row_frames[i]
                row.pack_forget()
                self.hidden_rows.append(row)
            self.row_frames = self.row_frames[:max_display]
        
        # Add new rows if we need more
        elif max_display > current_row_count:
            for i in range(current_row_count, max_display):
                if self.hidden_rows:
                    row = self.hidden_rows.pop()
                    self.update_player_row(row, i, self.players[i])
                    row.pack(fill='x', pady=1)
                    self.row_frames.append(row)
                else:
                    self.create_player_row(i, self.players[i])
        
        # Clear any existing "more players" label
        for child in self.table_frame.winfo_children():
            if isinstance(child, tk.Label) and not isinstance(child, tk.Frame):
                child.destroy()
        
        # If there are more players, show a message
        if len(self.players) > max_display:
            more_label = tk.Label(
                self.table_frame,
                text=f"... and {len(self.players) - max_display} more players. Use search to find specific players.",
                bg=DARK_THEME['bg_secondary'],
                fg=DARK_THEME['text_secondary'],
                font=(DARK_THEME['font_family'], 10, 'italic')
            )
            more_label.pack(pady=10)
        
        # Update scroll region
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
    
    def get_display_players(self):
        """Get top 10 players ensuring at least one from each main position"""
        # Check if we have players
        if not self.players:
            return []
            
        # If searching, show matching players
        search_text = self.search_var.get().lower() if hasattr(self, 'search_var') else ""
        if search_text:
            matching = [p for p in self.players if search_text in p.name.lower()]
            return matching[:10]
        
        # Get top 10 players but ensure at least one from each position
        all_top_players = self.players[:10]
        positions_needed = {'QB', 'RB', 'WR', 'TE'}
        positions_found = set()
        
        # Check which positions are already in top 10
        for player in all_top_players:
            positions_found.add(player.position)
        
        # If we're missing any positions, add the top player from each missing position
        if positions_found != positions_needed:
            result = list(all_top_players)
            for pos in positions_needed - positions_found:
                # Find the best player of this position
                pos_players = [p for p in self.players if p.position == pos]
                if pos_players:
                    # Remove the worst player from result and add this position player
                    if len(result) >= 10:
                        result.pop()
                    result.append(pos_players[0])
            
            # Re-sort by rank to maintain order
            result.sort(key=lambda p: p.rank)
            return result[:10]
        
        return all_top_players
    
    def update_player_row(self, row, index, player):
        """Update an existing row with new player data"""
        # Update background color
        bg = DARK_THEME['bg_tertiary'] if index % 2 == 0 else DARK_THEME['bg_secondary']
        row.configure(bg=bg)
        
        # Update player reference
        row.player = player
        row.index = index
        
        # Try to update existing widgets if they exist
        if hasattr(row, '_widgets_created'):
            self._update_existing_row_content(row, player, bg)
        else:
            # First time - create widgets
            for widget in row.winfo_children():
                widget.destroy()
            self._create_row_content(row, player, bg)
            row._widgets_created = True
    
    def _update_existing_row_content(self, row, player, bg):
        """Update existing row widgets with new player data"""
        # Update background colors
        for widget in row.winfo_children():
            if isinstance(widget, tk.Frame):
                widget.configure(bg=bg)
                for child in widget.winfo_children():
                    if hasattr(child, 'configure'):
                        try:
                            if hasattr(child, '_is_star_button'):
                                # Update star button
                                is_watched = player.player_id in self.watched_player_ids
                                child.configure(
                                    text="★" if is_watched else "☆",
                                    bg=bg,
                                    fg=DARK_THEME['text_accent'] if is_watched else DARK_THEME['text_muted'],
                                    activebackground=bg
                                )
                                child.configure(command=lambda p=player: self._toggle_watch_list(p))
                            elif isinstance(child, tk.Label):
                                if hasattr(child, '_field_type'):
                                    # Update specific field based on type
                                    if child._field_type == 'rank':
                                        child.configure(text=f"#{player.rank}", bg=bg)
                                    elif child._field_type == 'position':
                                        child.configure(text=player.position, bg=get_position_color(player.position))
                                        child.master.configure(bg=get_position_color(player.position))
                                    elif child._field_type == 'name':
                                        child.configure(text=player.format_name(), bg=bg)
                                    elif child._field_type == 'adp':
                                        child.configure(text=f"{player.adp:.1f}" if player.adp else '-', bg=bg)
                                    elif child._field_type == 'games':
                                        child.configure(text=str(getattr(player, 'games_2024', 0) or 0), bg=bg)
                                    elif child._field_type == 'points':
                                        points = getattr(player, 'points_2024', 0)
                                        child.configure(text=f"{points:.1f}" if points else "0.0", bg=bg)
                                    elif child._field_type == 'proj':
                                        proj = getattr(player, 'points_2025_proj', 0)
                                        child.configure(text=f"{proj:.1f}" if proj else "-", bg=bg)
                                    elif child._field_type == 'var':
                                        var_text = f"{player.var:.0f}" if hasattr(player, 'var') and player.var is not None else '-'
                                        child.configure(text=var_text, bg=bg)
                                else:
                                    child.configure(bg=bg)
                            elif isinstance(child, tk.Button) and hasattr(child, '_is_draft_button'):
                                # Update draft button state
                                child.configure(command=lambda p=player: self.on_draft_player(p))
                        except:
                            pass

    def create_player_row(self, index, player):
        """Create a row with player data"""
        # Row container
        bg = DARK_THEME['bg_tertiary'] if index % 2 == 0 else DARK_THEME['bg_secondary']
        row = tk.Frame(
            self.table_frame,
            bg=bg,
            height=35,
            relief='flat',
            bd=0
        )
        row.pack(fill='x', pady=1)
        row.pack_propagate(False)
        
        # Store the player reference on the row
        row.player = player
        row.index = index
        
        # Create row content
        self._create_row_content(row, player, bg)
        row._widgets_created = True
        
        self.row_frames.append(row)
    
    def _create_row_content(self, row, player, bg):
        """Create the content for a player row"""
        self._do_create_row_content(row, player, bg)
    
    def _do_create_row_content(self, row, player, bg):
        """Actually create the row content"""
        # Make row selectable
        def select_row(e=None):
            # Find current index of this player
            current_index = None
            for i, p in enumerate(self.players):
                if p == row.player:
                    current_index = i
                    break
            
            if current_index is not None:
                self.select_row(current_index)
                if self.on_select:
                    self.on_select(row.player)
        
        row.bind('<Button-1>', select_row)
        
        # Add drag support
        self._setup_drag_support(row)
        
        # Add double-click to draft
        def draft_on_double_click(e=None):
            if self.draft_enabled and self.on_draft:
                # Find current index of this player
                current_index = None
                for i, p in enumerate(self.players):
                    if p == row.player:
                        current_index = i
                        break
                
                if current_index is not None:
                    self.selected_index = current_index
                    self.on_draft()
        
        row.bind('<Double-Button-1>', draft_on_double_click)
        # Store the double-click handler on the row so cells can use it
        row._double_click_handler = draft_on_double_click
        
        # Bind mousewheel to this row
        if hasattr(self, '_mousewheel_handler'):
            row.bind('<MouseWheel>', self._mousewheel_handler)
        
        # Rank
        self.create_cell(row, f"#{player.rank}", 50, bg, select_row, field_type='rank')
        
        # Star button for watch list
        star_frame = tk.Frame(row, bg=bg, width=25)
        star_frame.pack(side='left', fill='y')
        star_frame.pack_propagate(False)
        
        is_watched = player.player_id in self.watched_player_ids
        star_btn = tk.Button(
            star_frame,
            text="★" if is_watched else "☆",
            bg=bg,
            fg=DARK_THEME['text_accent'] if is_watched else DARK_THEME['text_muted'],
            font=(DARK_THEME['font_family'], 12),
            bd=0,
            relief='flat',
            cursor='hand2',
            command=lambda p=player: self._toggle_watch_list(p),
            activebackground=bg
        )
        star_btn.pack(expand=True)
        star_btn._is_star_button = True  # Mark as star button to skip in drag handling
        row.star_button = star_btn  # Store reference for updates
        
        # Bind mousewheel
        if hasattr(self, '_mousewheel_handler'):
            star_frame.bind('<MouseWheel>', self._mousewheel_handler)
            star_btn.bind('<MouseWheel>', self._mousewheel_handler)
        
        # Position
        pos_frame = tk.Frame(row, bg=bg, width=45)
        pos_frame.pack(side='left', fill='y')
        pos_frame.pack_propagate(False)
        
        pos_inner = tk.Frame(pos_frame, bg=get_position_color(player.position), padx=8, pady=2)
        pos_inner.pack(expand=True)
        pos_label = tk.Label(pos_inner, text=player.position, bg=get_position_color(player.position), 
                            fg='white', font=(DARK_THEME['font_family'], 10, 'bold'))
        pos_label._field_type = 'position'
        pos_label.pack()
        pos_frame.bind('<Button-1>', select_row)
        
        # Bind double-click to position elements
        pos_frame.bind('<Double-Button-1>', row._double_click_handler)
        pos_inner.bind('<Double-Button-1>', row._double_click_handler)
        pos_label.bind('<Double-Button-1>', row._double_click_handler)
        
        # Bind mousewheel
        if hasattr(self, '_mousewheel_handler'):
            pos_frame.bind('<MouseWheel>', self._mousewheel_handler)
            pos_inner.bind('<MouseWheel>', self._mousewheel_handler)
            pos_label.bind('<MouseWheel>', self._mousewheel_handler)
        
        # Name
        self.create_cell(row, player.format_name(), 180, bg, select_row, anchor='w', field_type='name')
        
        # Team
        self.create_cell(row, player.team or '-', 45, bg, select_row, field_type='team')
        
        # ADP
        self.create_cell(row, f"{player.adp:.1f}" if player.adp else '-', 45, bg, select_row, field_type='adp')
        
        # 2024 Games
        games_text = str(getattr(player, 'games_2024', 0) or 0)
        self.create_cell(row, games_text, 40, bg, select_row, field_type='games')  # Updated to match header
        
        # 2024 Points
        points = getattr(player, 'points_2024', 0)
        points_text = f"{points:.1f}" if points else "0.0"
        self.create_cell(row, points_text, 75, bg, select_row, field_type='points')  # Updated to match header
        
        # Position Rank Projected
        pos_rank_proj_text = f"{player.position}{player.position_rank_proj}" if hasattr(player, 'position_rank_proj') and player.position_rank_proj else '-'
        self.create_cell(row, pos_rank_proj_text, 85, bg, select_row)  # Updated to match header
        
        # 2025 Projection
        proj = getattr(player, 'points_2025_proj', 0)
        proj_text = f"{proj:.1f}" if proj else "-"
        self.create_cell(row, proj_text, 75, bg, select_row, field_type='proj')  # Updated to match header
        
        # VAR (Value Above Replacement)
        var_text = f"{player.var:.0f}" if hasattr(player, 'var') and player.var is not None else '-'
        self.create_cell(row, var_text, 60, bg, select_row, field_type='var')  # Updated to match header
        
        # Draft button
        if self.draft_enabled:
            btn_frame = tk.Frame(row, bg=bg, width=80)
            btn_frame.pack(side='left', fill='y')
            btn_frame.pack_propagate(False)
            
            draft_btn = tk.Button(
                btn_frame,
                text='DRAFT',
                bg=DARK_THEME['button_active'],
                fg='white',
                font=(DARK_THEME['font_family'], 9, 'bold'),
                relief='flat',
                cursor='hand2',
                command=lambda p=player: self.draft_specific_player(p)
            )
            draft_btn._is_draft_button = True
            draft_btn.pack(expand=True)
            
            # Bind mousewheel
            if hasattr(self, '_mousewheel_handler'):
                btn_frame.bind('<MouseWheel>', self._mousewheel_handler)
                draft_btn.bind('<MouseWheel>', self._mousewheel_handler)
    
    def create_cell(self, parent, text, width, bg, click_handler, anchor='center', field_type=None):
        """Create a table cell with exact pixel width"""
        cell_frame = tk.Frame(parent, bg=bg, width=width)
        cell_frame.pack(side='left', fill='y')
        cell_frame.pack_propagate(False)
        
        cell = tk.Label(
            cell_frame,
            text=text,
            bg=bg,
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10),
            anchor=anchor
        )
        cell.pack(expand=True, fill='both')
        cell.bind('<Button-1>', click_handler)
        
        # Store field type for updates
        if field_type:
            cell._field_type = field_type
        
        # Also bind double-click if the parent row has it
        if hasattr(parent, '_double_click_handler'):
            cell.bind('<Double-Button-1>', parent._double_click_handler)
            cell_frame.bind('<Double-Button-1>', parent._double_click_handler)
        
        # Bind mousewheel
        if hasattr(self, '_mousewheel_handler'):
            cell_frame.bind('<MouseWheel>', self._mousewheel_handler)
            cell.bind('<MouseWheel>', self._mousewheel_handler)
        
        return cell
    
    def on_search_changed(self):
        """Handle search text changes"""
        search_text = self.search_var.get().lower()
        if search_text:
            # Filter players based on search
            filtered = [p for p in self.all_players if search_text in p.name.lower()]
            self.players = filtered
        else:
            # Show all players based on current filters
            self.update_players(self.all_players)
            return
        
        self.update_table_view()
    
    def select_row(self, index):
        """Highlight selected row"""
        self.selected_index = index
        selected_player = self.players[index] if index < len(self.players) else None
        
        for i, row in enumerate(self.row_frames):
            # Check if this row contains the selected player
            is_selected = hasattr(row, 'player') and row.player == selected_player
            
            if is_selected:
                row.configure(bg=DARK_THEME['button_active'])
                for widget in row.winfo_children():
                    if isinstance(widget, tk.Label):
                        widget.configure(bg=DARK_THEME['button_active'])
                    elif isinstance(widget, tk.Frame) and not any(isinstance(child, tk.Button) for child in widget.winfo_children()):
                        widget.configure(bg=DARK_THEME['button_active'])
                        # Update position badge background
                        for child in widget.winfo_children():
                            if isinstance(child, tk.Frame) and hasattr(row, 'player'):
                                # Keep position color for inner frame
                                continue
                            elif isinstance(child, tk.Label):
                                try:
                                    child.configure(bg=DARK_THEME['button_active'])
                                except:
                                    pass
            else:
                bg = DARK_THEME['bg_tertiary'] if i % 2 == 0 else DARK_THEME['bg_secondary']
                row.configure(bg=bg)
                for widget in row.winfo_children():
                    if isinstance(widget, tk.Label) and not widget.winfo_class() == 'Button':
                        widget.configure(bg=bg)
                    elif isinstance(widget, tk.Frame) and not any(isinstance(child, tk.Button) for child in widget.winfo_children()):
                        widget.configure(bg=bg)
                        # Update children of frames
                        for child in widget.winfo_children():
                            if isinstance(child, tk.Label) and child.winfo_class() != 'Button':
                                try:
                                    child.configure(bg=bg)
                                except:
                                    pass
    
    def add_player_image(self, item, player):
        """Add player image to the table row"""
        # Get image
        player_image = self.image_service.get_image(player.player_id, size=(30, 24))
        if player_image:
            # Schedule image placement after the table is rendered
            self.after(10, lambda: self.place_image_on_row(item, player_image))
    
    def place_image_on_row(self, item, image):
        """Place image on the specific row"""
        try:
            # Get the bounding box of the item
            bbox = self.table.bbox(item, column='space')
            if bbox:
                x, y, width, height = bbox
                # Create label with image
                img_label = tk.Label(self.table, image=image, bg=DARK_THEME['bg_tertiary'])
                img_label.image = image  # Keep reference
                img_label.place(x=x+10, y=y+3, width=30, height=24)
                self.image_labels.append(img_label)
                self.image_references.append(image)
        except:
            pass  # Item might not be visible
    
    def on_table_scroll(self, event):
        """Handle table scroll to update image positions"""
        # Re-update the table view to reposition images
        self.after(10, self.reposition_images)
    
    def reposition_images(self):
        """Reposition all images after scroll"""
        # Clear existing image labels
        if hasattr(self, 'image_labels'):
            for label in self.image_labels:
                label.destroy()
        self.image_labels = []
        
        # Re-add images for visible items
        for i, (item, player) in enumerate(zip(self.table.get_children(), self.players)):
            if self.image_service and player.player_id:
                player_image = self.image_service.get_image(player.player_id, size=(30, 24))
                if player_image:
                    self.place_image_on_row(item, player_image)
    
    def on_table_select(self, event):
        """Handle table row selection"""
        selection = self.table.selection()
        if selection:
            item = selection[0]
            index = self.table.index(item)
            if index < len(self.players):
                self.selected_index = index
                if self.on_select:
                    self.on_select(self.players[index])
    
    def on_table_double_click(self, event):
        """Handle double-click on table row to draft"""
        selection = self.table.selection()
        if selection and self.draft_enabled:
            item = selection[0]
            index = self.table.index(item)
            if index < len(self.players) and self.on_draft:
                self.selected_index = index
                self.on_draft()
    
    def sort_table_by(self, column: str):
        """Sort the table by the specified column"""
        # Sort the players list based on column
        if column == 'rank':
            self.players.sort(key=lambda p: p.rank)
        elif column == 'position':
            self.players.sort(key=lambda p: p.position)
        elif column == 'name':
            self.players.sort(key=lambda p: p.name)
        elif column == 'team':
            self.players.sort(key=lambda p: p.team if p.team else 'ZZZ')
        elif column == 'adp':
            self.players.sort(key=lambda p: p.adp if p.adp else float('inf'))
        
        # Update the table view
        self.update_table_view()
    
    def _setup_drag_support(self, row):
        """Setup drag and right-click support for a player row"""
        # Setup drag support - store initial position to distinguish drag from click
        def on_mouse_down(e, r=row):
            self.drag_start_pos = (e.x_root, e.y_root)
            self.is_dragging = False
            self.potential_drag_row = r
        
        def on_mouse_move(e):
            if self.drag_start_pos and not self.is_dragging:
                # Check if mouse moved enough to start drag (5 pixel threshold)
                dx = abs(e.x_root - self.drag_start_pos[0])
                dy = abs(e.y_root - self.drag_start_pos[1])
                if dx > 5 or dy > 5:
                    self.is_dragging = True
                    self._start_drag(e, self.potential_drag_row)
            elif self.is_dragging:
                self._on_drag_motion(e)
        
        def on_mouse_up(e):
            if self.is_dragging:
                self._end_drag(e)
            self.drag_start_pos = None
            self.is_dragging = False
            self.potential_drag_row = None
        
        # Bind to row and all children
        widgets_to_bind = [row]
        for child in row.winfo_children():
            widgets_to_bind.append(child)
            if hasattr(child, 'winfo_children'):
                for grandchild in child.winfo_children():
                    # Skip the star button
                    if not hasattr(grandchild, '_is_star_button'):
                        widgets_to_bind.append(grandchild)
        
        for widget in widgets_to_bind:
            widget.bind('<Button-1>', on_mouse_down, add='+')
            widget.bind('<B1-Motion>', on_mouse_move, add='+')
            widget.bind('<ButtonRelease-1>', on_mouse_up, add='+')
            
            # Add right-click menu
            widget.bind('<Button-3>', lambda e, r=row: self._show_context_menu(e, r))
    
    def _start_drag(self, event, row):
        """Start dragging a player"""
        if not hasattr(row, 'player'):
            return
        self.dragging_player = row.player
        
        # Create drag preview window
        if self.drag_window:
            self.drag_window.destroy()
            
        self.drag_window = tk.Toplevel(self)
        self.drag_window.overrideredirect(True)
        self.drag_window.attributes('-alpha', 0.8)
        
        # Create preview content
        preview_frame = StyledFrame(self.drag_window, bg_type='secondary')
        preview_frame.pack()
        
        # Position badge
        pos_label = tk.Label(
            preview_frame,
            text=self.dragging_player.position,
            bg=get_position_color(self.dragging_player.position),
            fg='white',
            font=(DARK_THEME['font_family'], 9, 'bold'),
            padx=8,
            pady=4
        )
        pos_label.pack(side='left', padx=(5, 10))
        
        # Player name
        name_label = tk.Label(
            preview_frame,
            text=self.dragging_player.format_name()[:25],
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10),
            padx=10,
            pady=5
        )
        name_label.pack(side='left')
        
        # Position window at cursor
        self.drag_window.geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
        
        # Change cursor
        self.config(cursor='hand2')
    
    def _on_drag_motion(self, event):
        """Update drag preview position"""
        if self.drag_window and self.drag_window.winfo_exists():
            self.drag_window.geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
    
    def _end_drag(self, event):
        """End drag operation"""
        if self.drag_window:
            self.drag_window.destroy()
            self.drag_window = None
        
        self.config(cursor='')
        
        # Check if dropped on watch list
        if self.dragging_player:
            # Get the widget under the cursor
            x, y = event.x_root, event.y_root
            target = self.winfo_containing(x, y)
            
            # Walk up the widget hierarchy to find if we're over the watch list
            while target:
                if hasattr(target, '__class__') and target.__class__.__name__ == 'WatchList':
                    # Add player to watch list
                    target.add_player(self.dragging_player)
                    self.watched_player_ids.add(self.dragging_player.player_id)
                    self._update_star_icons()
                    break
                target = target.master if hasattr(target, 'master') else None
        
        self.dragging_player = None
    
    def _show_context_menu(self, event, row):
        """Show right-click context menu"""
        if not hasattr(row, 'player'):
            return
            
        menu = tk.Menu(self, tearoff=0, bg=DARK_THEME['bg_secondary'], 
                      fg=DARK_THEME['text_primary'], 
                      activebackground=DARK_THEME['button_active'],
                      activeforeground='white')
        
        player = row.player
        if player.player_id in self.watched_player_ids:
            menu.add_command(label="Remove from Watch List", 
                           command=lambda: self._toggle_watch_list(player))
        else:
            menu.add_command(label="Add to Watch List", 
                           command=lambda: self._toggle_watch_list(player))
        
        menu.add_separator()
        menu.add_command(label="Draft Player", 
                        command=lambda: self.draft_specific_player(player),
                        state='normal' if self.draft_enabled else 'disabled')
        
        menu.post(event.x_root, event.y_root)
    
    def _toggle_watch_list(self, player):
        """Toggle player in watch list"""
        if self.watch_list_ref:
            if player.player_id in self.watched_player_ids:
                self.watch_list_ref.remove_player(player)
                self.watched_player_ids.discard(player.player_id)
            else:
                self.watch_list_ref.add_player(player)
                self.watched_player_ids.add(player.player_id)
            
            # Update star icon for this player
            self._update_star_icons()
    
    def _update_star_icons(self):
        """Update all star icons based on watched status"""
        for row in self.row_frames:
            if hasattr(row, 'star_button') and hasattr(row, 'player'):
                is_watched = row.player.player_id in self.watched_player_ids
                row.star_button.config(
                    text="★" if is_watched else "☆",
                    fg=DARK_THEME['text_accent'] if is_watched else DARK_THEME['text_muted']
                )
    
    def set_watch_list_ref(self, watch_list):
        """Set reference to watch list widget"""
        self.watch_list_ref = watch_list
        if watch_list:
            # Sync watched player IDs
            self.watched_player_ids = watch_list.watched_player_ids