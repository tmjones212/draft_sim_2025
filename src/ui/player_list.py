import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Optional, Callable, Dict
import os
from ..models import Player
from .theme import DARK_THEME, get_position_color
from .styled_widgets import StyledFrame
from .player_stats_popup import PlayerStatsPopup
from ..services.custom_adp_manager import CustomADPManager
from ..services.custom_round_manager import CustomRoundManager
from ..services.vegas_props_service import VegasPropsService
from ..services.sos_manager import SOSManager
from ..nfc_adp_fetcher import NFCADPFetcher


class PlayerList(StyledFrame):
    def __init__(self, parent, on_select: Optional[Callable] = None, on_draft: Optional[Callable] = None, on_adp_change: Optional[Callable] = None, image_service=None, **kwargs):
        super().__init__(parent, bg_type='secondary', **kwargs)
        self.on_select = on_select
        self.on_draft = on_draft
        self.on_adp_change = on_adp_change
        self.players: List[Player] = []
        self.selected_index = None
        self.image_cache = {}  # Cache loaded images
        self.player_cards = []
        self.draft_enabled = False
        self.image_service = image_service
        self.all_players: List[Player] = []  # Store all players
        self.selected_position = "ALL"  # Current filter
        self.current_pick = 0  # Track current pick number for BPA calculation
        self.user_team = None  # Track user's team for position needs
        self.sort_by = "adp"  # Default sort by ADP
        self.sort_ascending = True  # Track sort direction
        self.dragging_player = None  # Track dragged player
        self.drag_window = None  # Drag preview window
        self.watched_player_ids = set()  # Track watched players
        self.watch_list_ref = None  # Reference to watch list widget
        self.drag_start_pos = None  # Track drag start position
        self.is_dragging = False  # Track if actually dragging
        self.drafted_players = set()  # Track drafted players
        
        # Custom rankings from cheat sheet
        self.custom_rankings = {}
        self.player_tiers = {}
        
        # Add player ID to row mapping for better tracking
        self.player_id_to_row: Dict[str, tk.Frame] = {}
        
        # Initialize custom ADP manager
        self.custom_adp_manager = CustomADPManager()
        
        # Initialize custom round manager
        self.custom_round_manager = CustomRoundManager()
        
        # Reference to cheat sheet page for round assignments
        self.cheat_sheet_ref = None
        
        # Initialize Vegas props service with callback to refresh when loaded
        self.vegas_props_service = VegasPropsService(
            on_props_loaded=lambda: self._on_vegas_props_loaded()
        )
        
        # Initialize SOS manager
        self.sos_manager = SOSManager()
        
        # Initialize NFC ADP fetcher
        self.nfc_adp_fetcher = NFCADPFetcher()
        self.nfc_adp_data = self.nfc_adp_fetcher.load_nfc_adp()
        
        # Row management for performance
        self.row_frames = []  # Active row frames
        self.hidden_rows = []  # Hidden rows for reuse
        
        # Virtual scrolling
        self.visible_rows = 15  # Number of rows visible at once
        self.row_height = 35  # Height of each row
        self.top_index = 0  # Index of first visible row
        
        # Initialize position cache
        self._position_cache = {
            'players': None,
            'ALL': [],
            'OFF': [],
            'QB': [],
            'RB': [],
            'WR': [],
            'TE': [],
            'FLEX': [],
            'LB': [],
            'DB': []
        }
        
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
        
        # Reset ADP button
        self.reset_adp_button = tk.Button(
            header_frame,
            text="RESET ADP",
            bg=DARK_THEME['button_bg'],
            fg='white',
            font=(DARK_THEME['font_family'], 9, 'bold'),
            bd=0,
            relief='flat',
            padx=10,
            pady=4,
            command=self.reset_all_adp,
            cursor='hand2'
        )
        self.reset_adp_button.pack(side='right', padx=5)
        
        # Position filter buttons
        filter_frame = StyledFrame(header_frame, bg_type='secondary')
        filter_frame.pack(side='left', padx=20)
        
        # Add position filter buttons
        positions = ["ALL", "OFF", "QB", "RB", "WR", "TE", "FLEX", "LB", "DB"]
        self.position_buttons = {}
        
        for pos in positions:
            # Use position colors for filter buttons
            if pos == "ALL":
                btn_bg = DARK_THEME['button_active']
            elif pos in ["FLEX", "OFF"]:
                btn_bg = DARK_THEME['button_active'] if pos == self.selected_position else DARK_THEME['button_bg']
            elif pos in ["QB", "RB", "WR", "TE", "LB", "DB"]:
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
        
        # Suggested picks section (initially hidden)
        self.create_suggested_picks_section()
        
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
            ('Rank', 50, 'var'),  # Changed to sort by VAR when clicking Rank column
            ('CR', 35, 'custom_rank'),  # Custom Rank
            ('', 25, None),      # Star column
            ('BPA', 35, None),   # BPA indicator
            ('Pos', 45, 'position'),
            ('', 25, None),      # Info button column
            ('Name', 155, 'name'),
            ('Team', 45, 'team'),
            ('Bye', 35, 'bye_week'),  # Bye week column
            ('SOS', 40, 'sos'),  # Strength of Schedule column
            ('ADP', 55, 'adp'),  # Editable column
            ('NFC ADP', 70, 'nfc_adp'),  # NFC ADP column
            ('Rd', 35, None),    # Round tag column
            ('GP', 40, 'games_2024'),  # Added 5px
            ('2024 Pts', 75, 'points_2024'),  # Added 10px
            ('Proj Rank', 85, 'position_rank_proj'),  # Added 10px
            ('Proj Pts', 75, 'points_2025_proj'),  # Added 10px
            ('VAR', 60, 'var'),  # Added 10px
            ('Vegas', 160, None)  # Vegas props column - reduced to accommodate SOS
        ]
        
        for text, width, sort_key in headers:
            header_frame = tk.Frame(header_container, bg=DARK_THEME['bg_tertiary'], width=width)
            header_frame.pack(side='left', fill='y')
            header_frame.pack_propagate(False)
            
            # Add sort indicator to default sort column
            display_text = text
            if sort_key == 'adp' and not hasattr(self, '_sort_initialized'):
                display_text = text + ' ▲'  # Default sort by ADP ascending
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
        
        # Row frame references are already initialized in __init__
        self.selected_row = None
    
    def update_players(self, players: List[Player], limit: int = 30, force_refresh: bool = False):
        # Store all players
        self.all_players = players
        
        # Update position full indicators after updating players
        if hasattr(self, 'row_frames') and self.row_frames and self.user_team:
            self._update_position_full_indicators()
        
        # Apply custom ADP values to all players only if needed
        if not hasattr(self, '_last_custom_adp_applied') or self._last_custom_adp_applied != id(players):
            self.custom_adp_manager.apply_custom_adp_to_players(players)
            self._last_custom_adp_applied = id(players)
        
        # Pre-compute position groups for faster filtering if players list changed
        if not hasattr(self, '_position_cache') or self._position_cache.get('players') != id(players):
            self._position_cache = {
                'players': id(players),
                'ALL': players[:],  # Copy of all players
                'OFF': [],  # Offensive players (QB, RB, WR, TE)
                'QB': [],
                'RB': [],
                'WR': [],
                'TE': [],
                'FLEX': [],
                'LB': [],
                'DB': []
            }
            
            # Single pass through players to categorize
            for p in players:
                if p.position == 'QB':
                    self._position_cache['QB'].append(p)
                    self._position_cache['OFF'].append(p)
                elif p.position == 'RB':
                    self._position_cache['RB'].append(p)
                    self._position_cache['FLEX'].append(p)
                    self._position_cache['OFF'].append(p)
                elif p.position == 'WR':
                    self._position_cache['WR'].append(p)
                    self._position_cache['FLEX'].append(p)
                    self._position_cache['OFF'].append(p)
                elif p.position == 'TE':
                    self._position_cache['TE'].append(p)
                    self._position_cache['FLEX'].append(p)
                    self._position_cache['OFF'].append(p)
                elif p.position == 'LB':
                    self._position_cache['LB'].append(p)
                elif p.position == 'DB':
                    self._position_cache['DB'].append(p)
        
        # Use pre-computed lists
        filtered_players = self._position_cache.get(self.selected_position, [])[:]
        
        # Apply sorting and update
        self._apply_sort_and_update(filtered_players)
    
    def _complete_refresh_table(self):
        """Complete refresh of table"""
        self._smart_update_table()
    
    def remove_players(self, players_to_remove: List[Player], force_refresh: bool = False):
        """Remove multiple players from the list efficiently"""
        if not players_to_remove:
            return
        
        # Add to drafted players set
        for player in players_to_remove:
            if hasattr(player, 'player_id'):
                self.drafted_players.add(player)
        
        # Clear position cache since players are being removed
        if hasattr(self, '_position_cache'):
            delattr(self, '_position_cache')
        
        # If force_refresh is requested or we have too few displayed rows, do a full refresh
        if force_refresh or len(self.row_frames) < 5:
            # Create a set of player IDs for O(1) lookup
            player_ids_to_remove = {p.player_id for p in players_to_remove if p.player_id}
            # Remove from data
            self.players = [p for p in self.players if p.player_id not in player_ids_to_remove]
            self._smart_update_table()
            return
        
        # Create a set of player IDs for O(1) lookup
        player_ids_to_remove = {p.player_id for p in players_to_remove if p.player_id}
        
        # Find which rows to remove
        rows_to_remove = []
        for i, row in enumerate(self.row_frames):
            if hasattr(row, 'player') and hasattr(row.player, 'player_id') and row.player.player_id in player_ids_to_remove:
                rows_to_remove.append((i, row))
        
        # Remove from data
        self.players = [p for p in self.players if p.player_id not in player_ids_to_remove]
        
        # Fast path: just hide the specific rows without recreating everything
        if rows_to_remove:
            # First, hide rows that need to be removed
            for idx, row in rows_to_remove:
                row.pack_forget()
                # Remove from player ID mapping
                if hasattr(row, 'player') and row.player.player_id in self.player_id_to_row:
                    del self.player_id_to_row[row.player.player_id]
                
            # Remove from our list (in reverse order to maintain indices)
            for idx, row in sorted(rows_to_remove, reverse=True):
                self.row_frames.remove(row)
                self.hidden_rows.append(row)
            
            # Now we need to fill in the gaps with players that weren't displayed
            num_removed = len(rows_to_remove)
            current_displayed = len(self.row_frames)
            
            # Add new rows from the remaining players if we have space
            max_display = 25  # Match the limit in _smart_update_table  
            if current_displayed < max_display and current_displayed < len(self.players):
                for i in range(current_displayed, min(current_displayed + num_removed, len(self.players), max_display)):
                    player = self.players[i]
                    # Reuse or create row
                    if self.hidden_rows:
                        row = self.hidden_rows.pop()
                        for widget in row.winfo_children():
                            widget.destroy()
                    else:
                        row = tk.Frame(
                            self.table_frame,
                            height=self.row_height,
                            relief='flat',
                            bd=0
                        )
                    
                    # Configure and pack row
                    bg = DARK_THEME['bg_tertiary'] if len(self.row_frames) % 2 == 0 else DARK_THEME['bg_secondary']
                    row.configure(bg=bg)
                    row.pack(fill='x', pady=1)
                    row.pack_propagate(False)
                    
                    # Store player data
                    row.player = player
                    row.player_id = player.player_id
                    row.index = len(self.row_frames)
                    
                    # Track by player ID
                    if player.player_id:
                        self.player_id_to_row[player.player_id] = row
                    
                    # Create row content
                    self._create_row_content(row, player, bg)
                    
                    self.row_frames.append(row)
            
            # Update indices and colors for all rows
            for i, row in enumerate(self.row_frames):
                row.index = i
                # Update background color
                bg = DARK_THEME['bg_tertiary'] if i % 2 == 0 else DARK_THEME['bg_secondary']
                self._update_row_background(row, bg)
            
            # Update scroll region
            self.table_frame.update_idletasks()
            self.canvas.configure(scrollregion=self.canvas.bbox('all'))
    
    def _apply_sort_and_update(self, filtered_players=None):
        """Apply sorting to filtered players and update display"""
        if filtered_players is None:
            # Initialize position cache if it doesn't exist
            if not hasattr(self, '_position_cache'):
                self._position_cache = {
                    'players': None,
                    'ALL': [],
                    'OFF': [],
                    'QB': [],
                    'RB': [],
                    'WR': [],
                    'TE': [],
                    'FLEX': [],
                    'LB': [],
                    'DB': []
                }
                # If we have players, populate the cache
                if hasattr(self, 'players') and self.players:
                    self._position_cache['ALL'] = self.players[:]
            filtered_players = self._position_cache.get(self.selected_position, [])[:]
        
        # Cache sort keys to avoid repeated attribute lookups
        if self.sort_by == "rank":
            filtered_players.sort(key=lambda p: p.rank, reverse=not self.sort_ascending)
        elif self.sort_by == "custom_rank":
            filtered_players.sort(key=lambda p: self.custom_rankings.get(p.player_id, p.rank + 1000), reverse=not self.sort_ascending)
        elif self.sort_by == "adp":
            filtered_players.sort(key=lambda p: p.adp if p.adp else float('inf'), reverse=not self.sort_ascending)
        elif self.sort_by == "nfc_adp":
            filtered_players.sort(key=lambda p: getattr(p, 'nfc_adp', float('inf')), reverse=not self.sort_ascending)
        elif self.sort_by == "games_2024":
            filtered_players.sort(key=lambda p: getattr(p, 'games_2024', 0) or 0, reverse=not self.sort_ascending)
        elif self.sort_by == "points_2024":
            filtered_players.sort(key=lambda p: getattr(p, 'points_2024', 0) or 0, reverse=not self.sort_ascending)
        elif self.sort_by == "points_2025_proj":
            filtered_players.sort(key=lambda p: getattr(p, 'points_2025_proj', 0) or 0, reverse=not self.sort_ascending)
        elif self.sort_by == "position_rank_proj":
            # Sort by position rank (number first, then position)
            def get_proj_rank_key(p):
                proj_rank = getattr(p, 'position_rank_proj', '-')
                if proj_rank == '-' or not proj_rank:
                    return (999, 'ZZZ')
                # Extract position and number from something like 'QB1' or 'RB12'
                if isinstance(proj_rank, str):
                    pos = ''.join(c for c in proj_rank if c.isalpha())
                    num = ''.join(c for c in proj_rank if c.isdigit())
                    return (int(num) if num else 999, pos)
                return (999, 'ZZZ')
            filtered_players.sort(key=get_proj_rank_key, reverse=not self.sort_ascending)
        elif self.sort_by == "var":
            filtered_players.sort(key=lambda p: getattr(p, 'var', -100) if getattr(p, 'var', None) is not None else -100, reverse=not self.sort_ascending)
        elif self.sort_by == "sos":
            # Sort by SOS (lower is easier/better)
            def get_sos_key(p):
                sos = self.sos_manager.get_sos(p.team, p.position)
                return sos if sos is not None else 999
            filtered_players.sort(key=get_sos_key, reverse=not self.sort_ascending)
        elif self.sort_by == "position":
            filtered_players.sort(key=lambda p: p.position if p.position else 'ZZZ', reverse=not self.sort_ascending)
        elif self.sort_by == "name":
            filtered_players.sort(key=lambda p: p.name if p.name else 'ZZZ', reverse=not self.sort_ascending)
        elif self.sort_by == "team":
            filtered_players.sort(key=lambda p: p.team if p.team else 'ZZZ', reverse=not self.sort_ascending)
        elif self.sort_by == "bye_week":
            filtered_players.sort(key=lambda p: p.bye_week if p.bye_week else 999, reverse=not self.sort_ascending)
        else:
            filtered_players.sort(key=lambda p: p.rank, reverse=not self.sort_ascending)
        
        self.players = filtered_players
        self.selected_index = None
        
        # Always use smart update for performance
        self._smart_update_table()
    
    def _smart_update_table(self):
        """Smart update table - optimized but showing all players"""
        # Clear all rows first
        for row in self.row_frames:
            row.pack_forget()
            self.hidden_rows.append(row)
        self.row_frames.clear()
        self.player_id_to_row.clear()
        
        # Show only top players for performance
        max_display = min(25, len(self.players))  # Reduce to 25 for faster performance
        
        for i in range(max_display):
            player = self.players[i]
            # Reuse or create row
            if self.hidden_rows:
                row = self.hidden_rows.pop()
                for widget in row.winfo_children():
                    widget.destroy()
            else:
                row = tk.Frame(
                    self.table_frame,
                    height=self.row_height,
                    relief='flat',
                    bd=0
                )
            
            # Configure and pack row
            bg = DARK_THEME['bg_tertiary'] if i % 2 == 0 else DARK_THEME['bg_secondary']
            row.configure(bg=bg)
            row.pack(fill='x', pady=1)
            row.pack_propagate(False)
            
            # Store player data
            row.player = player
            row.player_id = player.player_id
            row.index = i
            
            # Track by player ID
            if player.player_id:
                self.player_id_to_row[player.player_id] = row
            
            # Create row content
            self._create_row_content(row, player, bg)
            
            self.row_frames.append(row)
        
        # Don't show more players message to keep it clean
        
        # Update scroll region
        self.table_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
    
    def _update_visible_rows(self):
        """Compatibility method for scroll events"""
        # No longer needed with full display
        pass
    
    def _update_row_data(self, row, index, player):
        """Update an existing row with new player data"""
        # Clear all existing content
        for widget in row.winfo_children():
            widget.destroy()
        
        # Update row data
        row.player = player
        row.player_id = player.player_id
        row.index = index
        
        # Update player ID mapping
        if player.player_id:
            # Remove old mapping if exists
            old_player_id = None
            for pid, r in self.player_id_to_row.items():
                if r == row:
                    old_player_id = pid
                    break
            if old_player_id:
                del self.player_id_to_row[old_player_id]
            
            # Add new mapping
            self.player_id_to_row[player.player_id] = row
        
        # Set background
        bg = DARK_THEME['bg_tertiary'] if index % 2 == 0 else DARK_THEME['bg_secondary']
        row.configure(bg=bg)
        
        # Create row content
        self._create_row_content(row, player, bg)
    
    def create_player_row(self, index, player):
        """Create a row with player data"""
        # Check if we need a tier break
        show_tier_break = False
        if index > 0 and hasattr(self, 'players'):
            prev_player = self.players[index - 1]
            curr_tier = self.calculate_player_tier(player)
            prev_tier = self.calculate_player_tier(prev_player)
            show_tier_break = curr_tier != prev_tier and curr_tier > 0 and prev_tier > 0
        
        # Add tier break if needed
        if show_tier_break:
            tier_break = tk.Frame(self.table_frame, bg=DARK_THEME['button_bg'], height=2)
            tier_break.pack(fill='x', padx=20, pady=3)
            
            # Add tier label
            tier_label = tk.Label(
                self.table_frame,
                text=f"━━━ Tier {curr_tier} ━━━",
                bg=DARK_THEME['bg_secondary'],
                fg=DARK_THEME['text_muted'],
                font=(DARK_THEME['font_family'], 9)
            )
            tier_label.pack(pady=(0, 2))
        
        # Reuse or create row
        if self.hidden_rows:
            row = self.hidden_rows.pop()
            for widget in row.winfo_children():
                widget.destroy()
        else:
            row = tk.Frame(
                self.table_frame,
                height=self.row_height,
                relief='flat',
                bd=0
            )
        
        # Configure and pack row
        bg = DARK_THEME['bg_tertiary'] if index % 2 == 0 else DARK_THEME['bg_secondary']
        row.configure(bg=bg)
        row.pack(fill='x', pady=1)
        row.pack_propagate(False)
        
        # Store player data
        row.player = player
        row.player_id = player.player_id
        row.index = index
        
        # Track by player ID
        if player.player_id:
            self.player_id_to_row[player.player_id] = row
        
        # Create row content
        self._create_row_content(row, player, bg)
        
        self.row_frames.append(row)
    
    def _create_row_content(self, row, player, bg):
        """Create the content for a player row"""
        # Make row selectable
        def select_row(e=None):
            # Find current index of this player
            current_index = None
            for i, p in enumerate(self.players):
                if p.player_id == player.player_id:
                    current_index = i
                    break
            
            if current_index is not None:
                self.select_row(current_index)
                if self.on_select:
                    self.on_select(self.players[current_index])
        
        row.bind('<Button-1>', select_row)
        
        # Add drag support
        self._setup_drag_support(row)
        
        # Add double-click to draft
        def draft_on_double_click(e=None):
            if self.draft_enabled and self.on_draft:
                # Find current player in list
                current_player = None
                for p in self.players:
                    if p.player_id == player.player_id:
                        current_player = p
                        break
                
                if current_player:
                    # Find index
                    for i, p in enumerate(self.players):
                        if p.player_id == current_player.player_id:
                            self.selected_index = i
                            break
                    self.on_draft()
        
        row.bind('<Double-Button-1>', draft_on_double_click)
        row._double_click_handler = draft_on_double_click
        
        # Add right-click to draft
        def on_right_click(e):
            # Select the row first
            select_row(e)
            
            # Create context menu
            menu = tk.Menu(row, tearoff=0,
                          bg=DARK_THEME['bg_secondary'],
                          fg=DARK_THEME['text_primary'],
                          activebackground=DARK_THEME['button_active'],
                          activeforeground='white')
            
            if self.draft_enabled:
                menu.add_command(label=f"Draft {player.format_name()}",
                                command=lambda: self.draft_specific_player(player))
                menu.add_separator()
            
            menu.add_command(label="View Stats",
                            command=lambda: self._show_player_stats(player))
            
            menu.add_command(label="View Vegas Props",
                            command=lambda: self._show_vegas_props(player))
            
            # Show menu
            menu.post(e.x_root, e.y_root)
            return "break"
        
        row.bind('<Button-3>', on_right_click)
        
        # Bind mousewheel
        if hasattr(self, '_mousewheel_handler'):
            row.bind('<MouseWheel>', self._mousewheel_handler)
        
        # Create cells with player data
        # Rank (now showing VAR rank)
        # Calculate VAR rank dynamically based on current filtered players
        var_rank = 1
        if hasattr(player, 'var') and player.var is not None:
            # Count how many players have higher VAR
            for p in self.players:
                if hasattr(p, 'var') and p.var is not None and p.var > player.var:
                    var_rank += 1
        else:
            # If no VAR, use original rank
            var_rank = player.rank
        
        self.create_cell(row, f"#{var_rank}", 50, bg, select_row, field_type='rank')
        
        # Custom Rank with tier color
        custom_rank = self.custom_rankings.get(player.player_id, '')
        tier = self.player_tiers.get(player.player_id, 0)
        
        cr_frame = tk.Frame(row, bg=bg, width=35)
        cr_frame.pack(side='left', fill='y')
        cr_frame.pack_propagate(False)
        
        tier_colors = {
            1: '#FFD700',  # Gold
            2: '#C0C0C0',  # Silver
            3: '#CD7F32',  # Bronze
            4: '#4169E1',  # Royal Blue
            5: '#32CD32',  # Lime Green
            6: '#FF6347',  # Tomato
            7: '#9370DB',  # Medium Purple
            8: '#20B2AA',  # Light Sea Green
        }
        
        if custom_rank:
            cr_bg = tier_colors.get(tier, bg)
            cr_fg = 'black' if tier in [1, 2, 3, 5] else 'white' if tier > 0 else DARK_THEME['text_primary']
            cr_label = tk.Label(
                cr_frame,
                text=str(custom_rank),
                bg=cr_bg,
                fg=cr_fg,
                font=(DARK_THEME['font_family'], 9, 'bold'),
                anchor='center'
            )
            cr_label.pack(expand=True, fill='both' if tier > 0 else None, padx=2 if tier > 0 else 0, pady=2 if tier > 0 else 0)
            cr_label.bind('<Button-1>', select_row)
        else:
            cr_label = tk.Label(cr_frame, text='-', bg=bg, fg=DARK_THEME['text_muted'], font=(DARK_THEME['font_family'], 9))
            cr_label.pack(expand=True)
            cr_label.bind('<Button-1>', select_row)
        
        # Add double-click handler for drafting to CR column
        if hasattr(row, '_double_click_handler'):
            cr_label.bind('<Double-Button-1>', row._double_click_handler)
            cr_frame.bind('<Double-Button-1>', row._double_click_handler)
        
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
        star_btn._is_star_button = True
        row.star_button = star_btn
        
        # BPA indicator
        bpa_frame = tk.Frame(row, bg=bg, width=35)
        bpa_frame.pack(side='left', fill='y')
        bpa_frame.pack_propagate(False)
        
        # Calculate BPA indicator for this player
        # Find player's index in current filtered list
        player_index = None
        for idx, p in enumerate(self.players):
            if p.player_id == player.player_id:
                player_index = idx
                break
        
        bpa_info = self.calculate_bpa_indicator(player, player_index) if player_index is not None else None
        if bpa_info:
            bpa_label = tk.Label(
                bpa_frame,
                text=bpa_info['text'],
                bg=bpa_info['bg'],
                fg=bpa_info['fg'],
                font=(DARK_THEME['font_family'], 11, 'bold'),
                padx=5,
                pady=2
            )
            bpa_label.pack(expand=True)
            
            # Add tooltip
            self.create_tooltip(bpa_label, bpa_info['tooltip'])
        else:
            # Empty BPA column
            tk.Label(bpa_frame, text='', bg=bg).pack(expand=True)
        
        bpa_frame.bind('<Button-1>', select_row)
        
        # Position
        pos_frame = tk.Frame(row, bg=bg, width=45)
        pos_frame.pack(side='left', fill='y')
        pos_frame.pack_propagate(False)
        
        pos_inner = tk.Frame(pos_frame, bg=get_position_color(player.position), padx=8, pady=2)
        pos_inner.pack(expand=True)
        pos_label = tk.Label(pos_inner, text=player.position, bg=get_position_color(player.position), 
                            fg='white', font=(DARK_THEME['font_family'], 10, 'bold'))
        pos_label.pack()
        pos_frame.bind('<Button-1>', select_row)
        pos_frame.bind('<Double-Button-1>', row._double_click_handler)
        pos_inner.bind('<Double-Button-1>', row._double_click_handler)
        pos_label.bind('<Double-Button-1>', row._double_click_handler)
        
        # Stats info button
        info_frame = tk.Frame(row, bg=bg, width=25)
        info_frame.pack(side='left', fill='y')
        info_frame.pack_propagate(False)
        
        info_btn = tk.Button(
            info_frame,
            text="?",
            bg=bg,
            fg=DARK_THEME['text_muted'],
            font=(DARK_THEME['font_family'], 10, 'bold'),
            bd=0,
            relief='flat',
            cursor='hand2',
            command=lambda p=player: self._show_player_stats(p),
            activebackground=bg,
            width=2
        )
        info_btn.pack(expand=True)
        info_btn._is_info_button = True
        
        # Name - Store player reference on row for position checking
        row.player = player  # Make sure player is attached to row BEFORE creating cells
        self.create_cell(row, player.format_name(), 155, bg, select_row, anchor='w', field_type='name')
        
        # Team Logo
        self._create_team_logo_cell(row, player, bg, select_row)
        
        # Bye Week
        bye_text = str(player.bye_week) if player.bye_week else '-'
        self.create_cell(row, bye_text, 35, bg, select_row, field_type='bye')
        
        # SOS (Strength of Schedule)
        sos_value = self.sos_manager.get_sos(player.team, player.position)
        sos_text = self.sos_manager.get_sos_display(player.team, player.position)
        if not sos_text:
            sos_text = '-'
        
        # Create SOS cell with custom color
        sos_cell_frame = tk.Frame(row, bg=bg, width=40)
        sos_cell_frame.pack(side='left', fill='y')
        sos_cell_frame.pack_propagate(False)
        
        sos_color = self.sos_manager.get_sos_color(sos_value) if sos_value else DARK_THEME['text_muted']
        sos_font = (DARK_THEME['font_family'], 9, 'bold') if sos_value else (DARK_THEME['font_family'], 10)
        
        sos_label = tk.Label(
            sos_cell_frame,
            text=sos_text,
            bg=bg,
            fg=sos_color,
            font=sos_font,
            anchor='center'
        )
        sos_label.pack(expand=True, fill='both')
        sos_label.bind('<Button-1>', select_row)
        
        # Add double-click handler for drafting
        if hasattr(row, '_double_click_handler'):
            sos_label.bind('<Double-Button-1>', row._double_click_handler)
            sos_cell_frame.bind('<Double-Button-1>', row._double_click_handler)
        
        # ADP (editable)
        adp_text = f"{int(player.adp)}" if player.adp else '-'
        adp_cell = self.create_cell(row, adp_text, 55, bg, select_row, field_type='adp')
        # Make ADP cell look more clickable
        if player.adp:
            adp_cell.config(fg=DARK_THEME['text_accent'], cursor='hand2')
        
        # NFC ADP
        nfc_adp = self.nfc_adp_fetcher.get_player_nfc_adp(player.name)
        if nfc_adp:
            nfc_adp_text = f"{nfc_adp:.1f}"
        else:
            nfc_adp_text = "999"
        self.create_cell(row, nfc_adp_text, 70, bg, select_row, field_type='nfc_adp')
        
        # Round tag (check for custom round first)
        custom_round = self.custom_round_manager.get_custom_round(player.player_id)
        if custom_round:
            round_text = str(custom_round)
        else:
            round_text = self.calculate_draft_round(player) or '-'
        round_cell = self.create_round_tag_cell(row, player, round_text, 35, bg, select_row)
        
        # Stats
        games_text = str(getattr(player, 'games_2024', 0) or 0)
        self.create_cell(row, games_text, 40, bg, select_row, field_type='games')
        
        points = getattr(player, 'points_2024', 0)
        points_text = f"{points:.1f}" if points else "0.0"
        self.create_cell(row, points_text, 75, bg, select_row, field_type='points')
        
        # Position Rank Projected
        pos_rank_proj_text = f"{player.position}{player.position_rank_proj}" if hasattr(player, 'position_rank_proj') and player.position_rank_proj else '-'
        self.create_cell(row, pos_rank_proj_text, 85, bg, select_row)
        
        # 2025 Projection
        proj = getattr(player, 'points_2025_proj', 0)
        proj_text = f"{proj:.1f}" if proj else "-"
        self.create_cell(row, proj_text, 75, bg, select_row, field_type='proj')
        
        # VAR
        var_text = f"{player.var:.0f}" if hasattr(player, 'var') and player.var is not None else '-'
        self.create_cell(row, var_text, 60, bg, select_row, field_type='var')
        
        # Vegas Props
        vegas_text = self.vegas_props_service.get_summary_string(player.name)
        if not vegas_text:
            vegas_text = "-"
        vegas_cell = self.create_cell(row, vegas_text, 160, bg, select_row, field_type='vegas')
        
        # Add tooltip with full Vegas props on hover
        if vegas_text != "-":
            self._add_vegas_tooltip(vegas_cell, player)
        
        # No more draft button - users can double-click or right-click to draft
    
    def create_round_tag_cell(self, parent, player, round_text, width, bg, click_handler):
        """Create a cell with round tag styling and editing capability"""
        cell_frame = tk.Frame(parent, bg=bg, width=width)
        cell_frame.pack(side='left', fill='y')
        cell_frame.pack_propagate(False)
        
        # Style based on round
        if round_text == '-':
            # No round
            cell = tk.Label(
                cell_frame,
                text=round_text,
                bg=bg,
                fg=DARK_THEME['text_muted'],
                font=(DARK_THEME['font_family'], 9),
                anchor='center'
            )
            cell.pack(expand=True)
        else:
            # Create a styled round tag
            tag_frame = tk.Frame(cell_frame, bg=bg)
            tag_frame.pack(expand=True)
            
            # Determine color based on round
            try:
                round_num = int(round_text.replace('+', ''))
                if round_num <= 3:
                    tag_bg = '#FF5E5B'  # Red for early rounds
                    tag_fg = 'white'
                elif round_num <= 6:
                    tag_bg = '#FFB347'  # Orange for mid rounds
                    tag_fg = 'white'
                elif round_num <= 9:
                    tag_bg = '#4ECDC4'  # Teal for mid-late rounds
                    tag_fg = 'white'
                else:
                    tag_bg = '#7B68EE'  # Purple for late rounds
                    tag_fg = 'white'
            except:
                tag_bg = bg
                tag_fg = DARK_THEME['text_secondary']
            
            cell = tk.Label(
                tag_frame,
                text=f"R{round_text}",
                bg=tag_bg,
                fg=tag_fg,
                font=(DARK_THEME['font_family'], 9, 'bold'),
                padx=6,
                pady=1,
                anchor='center'
            )
            cell.pack()
        
        # Bind click handler - make it editable on single click
        def edit_round(e):
            self._edit_player_round(player, cell_frame)
            return "break"  # Prevent event propagation
        
        cell.bind('<Button-1>', edit_round)
        cell_frame.bind('<Button-1>', edit_round)
        
        # Make cursor indicate it's clickable
        cell.config(cursor='hand2')
        cell_frame.config(cursor='hand2')
        
        # Bind double-click if the parent row has it
        if hasattr(parent, '_double_click_handler'):
            cell.bind('<Double-Button-1>', parent._double_click_handler)
            cell_frame.bind('<Double-Button-1>', parent._double_click_handler)
        
        # Bind mousewheel
        if hasattr(self, '_mousewheel_handler'):
            cell_frame.bind('<MouseWheel>', self._mousewheel_handler)
            cell.bind('<MouseWheel>', self._mousewheel_handler)
        
        return cell
    
    def create_cell(self, parent, text, width, bg, click_handler, anchor='center', field_type=None):
        """Create a table cell with exact pixel width"""
        cell_frame = tk.Frame(parent, bg=bg, width=width)
        cell_frame.pack(side='left', fill='y')
        cell_frame.pack_propagate(False)
        
        # Determine text color based on position limits
        text_color = DARK_THEME['text_primary']
        if field_type == 'name' and hasattr(parent, 'player'):
            player = parent.player
            if self._is_position_full(player):
                text_color = '#FF5E5B'  # Red color for full positions
        
        cell = tk.Label(
            cell_frame,
            text=text,
            bg=bg,
            fg=text_color,
            font=(DARK_THEME['font_family'], 10),
            anchor=anchor
        )
        cell.pack(expand=True, fill='both')
        
        # Bind click handler only if not ADP field (ADP gets special handling below)
        if field_type != 'adp':
            cell.bind('<Button-1>', click_handler)
        
        # Store field type for updates
        if field_type:
            cell._field_type = field_type
            
            # Add click to edit ADP
            if field_type == 'adp' and hasattr(parent, 'player'):
                def edit_adp(e):
                    self._edit_player_adp(parent.player)
                    return "break"  # Prevent event propagation
                
                cell.bind('<Button-1>', edit_adp)
                cell_frame.bind('<Button-1>', edit_adp)
                cell.config(cursor='hand2')  # Show hand cursor to indicate it's clickable
                
                # Add subtle hover effect to show it's editable (no tooltip)
                def on_enter(e, c=cell):
                    c.config(fg='#4ECDC4')  # Bright teal to show editable
                    
                def on_leave(e, c=cell):
                    c.config(fg=DARK_THEME['text_primary'])
                        
                cell.bind('<Enter>', on_enter)
                cell.bind('<Leave>', on_leave)
        
        # Also bind double-click if the parent row has it (but not for ADP cells)
        if hasattr(parent, '_double_click_handler') and field_type != 'adp':
            cell.bind('<Double-Button-1>', parent._double_click_handler)
            cell_frame.bind('<Double-Button-1>', parent._double_click_handler)
        
        # Bind mousewheel
        if hasattr(self, '_mousewheel_handler'):
            cell_frame.bind('<MouseWheel>', self._mousewheel_handler)
            cell.bind('<MouseWheel>', self._mousewheel_handler)
        
        return cell
    
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
        # First check if player is in current filtered list
        for i, p in enumerate(self.players):
            if p.player_id == player.player_id:
                self.select_player(i)
                if self.on_draft:
                    self.on_draft()
                return
        
        # If not found in filtered list, temporarily clear filters to find the player
        # Save current filter state
        current_position = self.selected_position
        current_search = self.search_var.get()
        
        # Clear filters temporarily
        self.selected_position = "ALL"
        self.search_var.set("")
        self.update_players(self.all_players)
        
        # Now find the player
        for i, p in enumerate(self.players):
            if p.player_id == player.player_id:
                self.select_player(i)
                if self.on_draft:
                    self.on_draft()
                # Restore filters after drafting
                self.selected_position = current_position
                self.search_var.set(current_search)
                return
        
        # If still not found, restore filters
        self.selected_position = current_position
        self.search_var.set(current_search)
        self.update_players(self.all_players)
    
    def _show_player_stats(self, player: Player):
        """Show the player stats popup"""
        PlayerStatsPopup(self.winfo_toplevel(), player, self.image_service, self.all_players)
    
    def _add_vegas_tooltip(self, widget, player):
        """Add tooltip showing full Vegas props on hover"""
        tooltip = None
        
        def show_tooltip(event):
            nonlocal tooltip
            if tooltip:
                return
            
            # Get full props for player
            props = self.vegas_props_service.get_player_props(player.name)
            if not props:
                return
            
            # Create tooltip window
            tooltip = tk.Toplevel(self)
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
            
            frame = tk.Frame(tooltip, bg=DARK_THEME['bg_tertiary'], 
                           highlightbackground=DARK_THEME['border'], 
                           highlightthickness=1)
            frame.pack()
            
            # Title
            title = tk.Label(frame, text=f"Vegas Props - {player.format_name()}",
                           bg=DARK_THEME['bg_tertiary'], fg='white',
                           font=(DARK_THEME['font_family'], 11, 'bold'))
            title.pack(padx=10, pady=(5, 3))
            
            # Props data
            prop_labels = {
                'passing_yards': 'Passing Yards',
                'passing_tds': 'Passing TDs',
                'rushing_yards': 'Rushing Yards',
                'rushing_tds': 'Rushing TDs',
                'receiving_yards': 'Receiving Yards',
                'receiving_tds': 'Receiving TDs',
                'receptions': 'Receptions'
            }
            
            for prop_key, label in prop_labels.items():
                if prop_key in props:
                    prop = props[prop_key]
                    text = f"{label}: {prop.prop_value:.1f} (O{prop.over_line}/U{prop.under_line})"
                    lbl = tk.Label(frame, text=text,
                                 bg=DARK_THEME['bg_tertiary'], 
                                 fg=DARK_THEME['text_primary'],
                                 font=(DARK_THEME['font_family'], 10))
                    lbl.pack(padx=10, pady=2, anchor='w')
        
        def hide_tooltip(event):
            nonlocal tooltip
            if tooltip:
                tooltip.destroy()
                tooltip = None
        
        widget.bind('<Enter>', show_tooltip)
        widget.bind('<Leave>', hide_tooltip)
    
    def _show_vegas_props(self, player: Player):
        """Show detailed Vegas props in a popup"""
        props = self.vegas_props_service.get_player_props(player.name)
        if not props:
            messagebox.showinfo("No Vegas Props", 
                              f"No Vegas props available for {player.format_name()}")
            return
        
        # Create popup window
        popup = tk.Toplevel(self.winfo_toplevel())
        popup.title(f"Vegas Props - {player.format_name()}")
        popup.configure(bg=DARK_THEME['bg_primary'])
        popup.geometry("500x400")
        
        # Main frame
        main_frame = StyledFrame(popup, bg_type='primary')
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Title
        title = tk.Label(main_frame, 
                        text=f"{player.format_name()} - {player.position} - {player.team}",
                        bg=DARK_THEME['bg_primary'], fg='white',
                        font=(DARK_THEME['font_family'], 14, 'bold'))
        title.pack(pady=(0, 10))
        
        # Props frame
        props_frame = StyledFrame(main_frame, bg_type='secondary')
        props_frame.pack(fill='both', expand=True)
        
        # Display props
        prop_labels = {
            'passing_yards': ('Passing Yards', '#FF69B4'),
            'passing_tds': ('Passing TDs', '#FF69B4'),
            'rushing_yards': ('Rushing Yards', '#00CED1'),
            'rushing_tds': ('Rushing TDs', '#00CED1'),
            'receiving_yards': ('Receiving Yards', '#4169E1'),
            'receiving_tds': ('Receiving TDs', '#4169E1'),
            'receptions': ('Receptions', '#4169E1')
        }
        
        for prop_key, (label, color) in prop_labels.items():
            if prop_key in props:
                prop = props[prop_key]
                
                # Prop row
                row_frame = tk.Frame(props_frame, bg=DARK_THEME['bg_secondary'])
                row_frame.pack(fill='x', padx=10, pady=5)
                
                # Label
                lbl = tk.Label(row_frame, text=label + ":",
                             bg=DARK_THEME['bg_secondary'], fg=color,
                             font=(DARK_THEME['font_family'], 11, 'bold'),
                             width=15, anchor='w')
                lbl.pack(side='left')
                
                # Value
                value_text = f"{prop.prop_value:.1f}"
                value_lbl = tk.Label(row_frame, text=value_text,
                                   bg=DARK_THEME['bg_secondary'], fg='white',
                                   font=(DARK_THEME['font_family'], 11, 'bold'),
                                   width=8)
                value_lbl.pack(side='left', padx=(10, 20))
                
                # Odds
                odds_text = f"Over {prop.over_line}  /  Under {prop.under_line}"
                odds_lbl = tk.Label(row_frame, text=odds_text,
                                  bg=DARK_THEME['bg_secondary'], 
                                  fg=DARK_THEME['text_secondary'],
                                  font=(DARK_THEME['font_family'], 10))
                odds_lbl.pack(side='left')
    
    def filter_by_position(self, position: str):
        """Filter players by position"""
        self.selected_position = position
        
        # Update button appearances with position colors
        for pos, btn in self.position_buttons.items():
            if pos == position:
                if pos in ["ALL", "FLEX", "OFF"]:
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
        # Special columns that should only sort one way
        always_ascending = ['adp', 'nfc_adp']  # Always show lowest first
        always_descending = ['points_2024', 'points_2025_proj', 'var']  # Always show highest first
        
        # Check if this is a special column
        if sort_by in always_ascending:
            self.sort_by = sort_by
            self.sort_ascending = True
        elif sort_by in always_descending:
            self.sort_by = sort_by
            self.sort_ascending = False
        else:
            # Normal toggle behavior for other columns
            if self.sort_by == sort_by:
                self.sort_ascending = not self.sort_ascending
            else:
                # New column - set default sort direction
                self.sort_by = sort_by
                # Ascending first for: Pos, Name, Team, Proj Rank, Custom Rank
                if sort_by in ['position', 'name', 'team', 'position_rank_proj', 'custom_rank']:
                    self.sort_ascending = True
                else:
                    # Descending first for other columns
                    self.sort_ascending = False
        
        # Update header indicators
        self.update_sort_indicators()
        
        # Use cached sorted list if available
        self._apply_sort_and_update()
    
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
    
    def set_custom_rankings(self, custom_rankings, player_tiers):
        """Set custom rankings from cheat sheet"""
        self.custom_rankings = custom_rankings
        self.player_tiers = player_tiers
    
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
        
        self._complete_refresh_table()
    
    def select_row(self, index):
        """Highlight selected row"""
        self.selected_index = index
        selected_player = self.players[index] if index < len(self.players) else None
        
        for i, row in enumerate(self.row_frames):
            # Check if this row contains the selected player
            is_selected = hasattr(row, 'player') and row.player.player_id == selected_player.player_id
            
            if is_selected:
                row.configure(bg=DARK_THEME['button_active'])
                self._update_row_background(row, DARK_THEME['button_active'], is_selected=True)
            else:
                bg = DARK_THEME['bg_tertiary'] if i % 2 == 0 else DARK_THEME['bg_secondary']
                row.configure(bg=bg)
                self._update_row_background(row, bg, is_selected=False)
    
    def _update_row_background(self, row, bg, is_selected=False):
        """Update background color for a row and all its children"""
        row.configure(bg=bg)
        
        # Update all child widgets
        for widget in row.winfo_children():
            if isinstance(widget, tk.Frame):
                # Don't change position badge background unless selected
                has_position = any(isinstance(child, tk.Frame) and child.cget('bg') in ['#FF5E5B', '#23CDCD', '#5E9BFF', '#FF8C42'] for child in widget.winfo_children())
                
                if not has_position or is_selected:
                    widget.configure(bg=bg)
                    # Update label children
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Label):
                            # Skip position labels unless selected
                            if hasattr(child, 'master') and hasattr(child.master, 'cget'):
                                parent_bg = child.master.cget('bg')
                                if parent_bg in ['#FF5E5B', '#23CDCD', '#5E9BFF', '#FF8C42'] and not is_selected:
                                    continue
                            child.configure(bg=bg)
                        elif isinstance(child, tk.Button) and hasattr(child, '_is_star_button'):
                            child.configure(bg=bg, activebackground=bg)
            elif isinstance(widget, tk.Label):
                widget.configure(bg=bg)
    
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
        menu.add_command(label="Edit ADP", 
                        command=lambda: self._edit_player_adp(player))
        
        menu.add_separator()
        menu.add_command(label="Draft Player", 
                        command=lambda: self.draft_specific_player(player),
                        state='normal' if self.draft_enabled else 'disabled')
        
        menu.post(event.x_root, event.y_root)
    
    def _edit_player_adp(self, player):
        """Show dialog to edit player's ADP"""
        # Create dialog window
        dialog = tk.Toplevel(self)
        dialog.title(f"Edit ADP - {player.name}")
        dialog.geometry("350x200")
        dialog.configure(bg=DARK_THEME['bg_secondary'])
        dialog.transient(self.master)
        dialog.grab_set()
        
        # Center dialog on parent
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Player info
        info_frame = tk.Frame(dialog, bg=DARK_THEME['bg_secondary'])
        info_frame.pack(pady=10)
        
        player_label = tk.Label(
            info_frame,
            text=f"{player.name} ({player.position})",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 12, 'bold')
        )
        player_label.pack()
        
        current_label = tk.Label(
            info_frame,
            text=f"Current ADP: {player.adp:.1f}",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 10)
        )
        current_label.pack()
        
        # ADP input
        input_frame = tk.Frame(dialog, bg=DARK_THEME['bg_secondary'])
        input_frame.pack(pady=20)
        
        label = tk.Label(
            input_frame,
            text="New ADP:",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 11)
        )
        label.pack(side='left', padx=(0, 10))
        
        adp_var = tk.StringVar(value=f"{int(player.adp)}")
        entry = tk.Entry(
            input_frame,
            textvariable=adp_var,
            bg=DARK_THEME['bg_tertiary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 11),
            width=10
        )
        entry.pack(side='left')
        entry.focus()
        entry.select_range(0, tk.END)
        
        # Buttons
        button_frame = tk.Frame(dialog, bg=DARK_THEME['bg_secondary'])
        button_frame.pack(pady=10)
        
        def save_adp():
            try:
                new_adp = float(adp_var.get())
                if new_adp < 1.0 or new_adp > 300.0:
                    raise ValueError("ADP must be between 1.0 and 300.0")
                
                # Update player's ADP
                player.adp = new_adp
                
                # Save to custom ADP manager
                self.custom_adp_manager.set_custom_adp(player.player_id, new_adp)
                
                # Update the row display immediately
                for row in self.row_frames:
                    if hasattr(row, 'player') and row.player.player_id == player.player_id:
                        # Update player's ADP value for round calculation
                        row.player.adp = new_adp
                        
                        # Find and update the ADP cell
                        adp_updated = False
                        round_cell_frame = None
                        round_cell_index = 0
                        
                        for i, widget in enumerate(row.winfo_children()):
                            if isinstance(widget, tk.Frame):
                                for child in widget.winfo_children():
                                    if isinstance(child, tk.Label) and hasattr(child, '_field_type') and child._field_type == 'adp':
                                        child.config(text=f"{int(new_adp)}")
                                        adp_updated = True
                                        # Round cell should be the next frame
                                        round_cell_index = i + 1
                                        break
                        
                        # Update the round tag (it's the frame after ADP)
                        if adp_updated and round_cell_index < len(row.winfo_children()):
                            round_cell_frame = row.winfo_children()[round_cell_index]
                            if isinstance(round_cell_frame, tk.Frame):
                                # Recreate the round tag with new value
                                for widget in round_cell_frame.winfo_children():
                                    widget.destroy()
                                
                                # Get new round text
                                new_round_text = self.calculate_draft_round(row.player) or '-'
                                
                                # Recreate the round tag content
                                if new_round_text == '-':
                                    cell = tk.Label(
                                        round_cell_frame,
                                        text=new_round_text,
                                        bg=round_cell_frame['bg'],
                                        fg=DARK_THEME['text_muted'],
                                        font=(DARK_THEME['font_family'], 9),
                                        anchor='center'
                                    )
                                    cell.pack(expand=True)
                                else:
                                    tag_frame = tk.Frame(round_cell_frame, bg=round_cell_frame['bg'])
                                    tag_frame.pack(expand=True)
                                    
                                    # Determine color based on round
                                    try:
                                        round_num = int(new_round_text.replace('+', ''))
                                        if round_num <= 3:
                                            tag_bg = '#FF5E5B'  # Red for early rounds
                                            tag_fg = 'white'
                                        elif round_num <= 6:
                                            tag_bg = '#FFB347'  # Orange for mid rounds
                                            tag_fg = 'white'
                                        elif round_num <= 9:
                                            tag_bg = '#4ECDC4'  # Teal for mid-late rounds
                                            tag_fg = 'white'
                                        else:
                                            tag_bg = '#7B68EE'  # Purple for late rounds
                                            tag_fg = 'white'
                                    except:
                                        tag_bg = round_cell_frame['bg']
                                        tag_fg = DARK_THEME['text_secondary']
                                    
                                    cell = tk.Label(
                                        tag_frame,
                                        text=f"R{new_round_text}",
                                        bg=tag_bg,
                                        fg=tag_fg,
                                        font=(DARK_THEME['font_family'], 9, 'bold'),
                                        padx=6,
                                        pady=1,
                                        anchor='center'
                                    )
                                    cell.pack()
                        break
                
                # Re-sort if currently sorted by ADP
                if self.sort_by == 'adp':
                    # Trigger a full update with current players
                    self.update_players(self.all_players)
                
                # Notify main app that ADP has changed
                if self.on_adp_change:
                    self.on_adp_change()
                
                dialog.destroy()
                
            except ValueError as e:
                error_label = tk.Label(
                    dialog,
                    text=str(e) if "must be between" in str(e) else "Invalid ADP value",
                    bg=DARK_THEME['bg_secondary'],
                    fg='#ff6b6b',
                    font=(DARK_THEME['font_family'], 9)
                )
                error_label.pack(pady=5)
                dialog.after(3000, error_label.destroy)
        
        save_btn = tk.Button(
            button_frame,
            text="SAVE",
            command=save_adp,
            bg=DARK_THEME['button_active'],
            fg='white',
            font=(DARK_THEME['font_family'], 10, 'bold'),
            padx=20,
            pady=5,
            bd=0,
            highlightthickness=0
        )
        save_btn.pack(side='left', padx=5)
        
        cancel_btn = tk.Button(
            button_frame,
            text="CANCEL",
            command=dialog.destroy,
            bg=DARK_THEME['button_bg'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10),
            padx=20,
            pady=5,
            bd=0,
            highlightthickness=0
        )
        cancel_btn.pack(side='left', padx=5)
        
        # Bind Enter to save
        entry.bind('<Return>', lambda e: save_adp())
        
        # Bind Escape to cancel
        dialog.bind('<Escape>', lambda e: dialog.destroy())
    
    def _edit_player_round(self, player, cell_frame):
        """Show dialog to edit player's round assignment"""
        # Create dialog window
        dialog = tk.Toplevel(self)
        dialog.title(f"Assign Round - {player.name}")
        dialog.geometry("400x250")
        dialog.configure(bg=DARK_THEME['bg_secondary'])
        dialog.transient(self.master)
        dialog.grab_set()
        
        # Center dialog on parent
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Player info
        info_frame = tk.Frame(dialog, bg=DARK_THEME['bg_secondary'])
        info_frame.pack(pady=10)
        
        player_label = tk.Label(
            info_frame,
            text=f"{player.name} ({player.position})",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 12, 'bold')
        )
        player_label.pack()
        
        # Show current round
        current_round = self.custom_round_manager.get_custom_round(player.player_id)
        if not current_round:
            current_round = self.calculate_draft_round(player) or '-'
        
        current_label = tk.Label(
            info_frame,
            text=f"Current Round: {current_round}",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 10)
        )
        current_label.pack()
        
        adp_label = tk.Label(
            info_frame,
            text=f"ADP: {player.adp:.1f}" if player.adp else "ADP: -",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_muted'],
            font=(DARK_THEME['font_family'], 9)
        )
        adp_label.pack()
        
        # Round selection frame
        select_frame = tk.Frame(dialog, bg=DARK_THEME['bg_secondary'])
        select_frame.pack(pady=20)
        
        label = tk.Label(
            select_frame,
            text="Assign to Round:",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 11)
        )
        label.pack(pady=(0, 10))
        
        # Create round buttons in a grid
        rounds_frame = tk.Frame(select_frame, bg=DARK_THEME['bg_secondary'])
        rounds_frame.pack()
        
        def assign_round(round_num):
            """Assign player to specified round"""
            self.custom_round_manager.set_custom_round(player.player_id, round_num)
            
            # Update the round tag cell immediately
            for widget in cell_frame.winfo_children():
                widget.destroy()
            
            # Recreate the round tag content
            if round_num == 0:
                round_text = self.calculate_draft_round(player) or '-'
            else:
                round_text = str(round_num)
            
            # Style based on round
            if round_text == '-':
                cell = tk.Label(
                    cell_frame,
                    text=round_text,
                    bg=cell_frame['bg'],
                    fg=DARK_THEME['text_muted'],
                    font=(DARK_THEME['font_family'], 9),
                    anchor='center'
                )
                cell.pack(expand=True)
            else:
                tag_frame = tk.Frame(cell_frame, bg=cell_frame['bg'])
                tag_frame.pack(expand=True)
                
                # Determine color based on round
                try:
                    rnd = int(round_text.replace('+', ''))
                    if rnd <= 3:
                        tag_bg = '#FF5E5B'  # Red for early rounds
                        tag_fg = 'white'
                    elif rnd <= 6:
                        tag_bg = '#FFB347'  # Orange for mid rounds
                        tag_fg = 'white'
                    elif rnd <= 9:
                        tag_bg = '#4ECDC4'  # Teal for mid-late rounds
                        tag_fg = 'white'
                    else:
                        tag_bg = '#7B68EE'  # Purple for late rounds
                        tag_fg = 'white'
                except:
                    tag_bg = cell_frame['bg']
                    tag_fg = DARK_THEME['text_secondary']
                
                cell = tk.Label(
                    tag_frame,
                    text=f"R{round_text}",
                    bg=tag_bg,
                    fg=tag_fg,
                    font=(DARK_THEME['font_family'], 9, 'bold'),
                    padx=6,
                    pady=1,
                    anchor='center'
                )
                cell.pack()
            
            # Re-bind click handler
            def edit_round(e):
                self._edit_player_round(player, cell_frame)
                return "break"
            
            cell.bind('<Button-1>', edit_round)
            cell_frame.bind('<Button-1>', edit_round)
            cell.config(cursor='hand2')
            cell_frame.config(cursor='hand2')
            
            dialog.destroy()
        
        # Create round buttons (1-15)
        for i in range(3):
            row_frame = tk.Frame(rounds_frame, bg=DARK_THEME['bg_secondary'])
            row_frame.pack(pady=2)
            
            for j in range(5):
                round_num = i * 5 + j + 1
                if round_num <= 15:
                    # Determine button color
                    if round_num <= 3:
                        btn_bg = '#FF5E5B'  # Red
                    elif round_num <= 6:
                        btn_bg = '#FFB347'  # Orange
                    elif round_num <= 9:
                        btn_bg = '#4ECDC4'  # Teal
                    else:
                        btn_bg = '#7B68EE'  # Purple
                    
                    btn = tk.Button(
                        row_frame,
                        text=f"R{round_num}",
                        command=lambda r=round_num: assign_round(r),
                        bg=btn_bg,
                        fg='white',
                        font=(DARK_THEME['font_family'], 10, 'bold'),
                        width=5,
                        padx=5,
                        pady=5,
                        bd=0,
                        highlightthickness=0,
                        cursor='hand2'
                    )
                    btn.pack(side='left', padx=2)
        
        # Clear button
        clear_frame = tk.Frame(dialog, bg=DARK_THEME['bg_secondary'])
        clear_frame.pack(pady=10)
        
        clear_btn = tk.Button(
            clear_frame,
            text="CLEAR CUSTOM ROUND",
            command=lambda: assign_round(0),
            bg=DARK_THEME['button_bg'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10),
            padx=20,
            pady=5,
            bd=0,
            highlightthickness=0
        )
        clear_btn.pack()
        
        # Bind Escape to cancel
        dialog.bind('<Escape>', lambda e: dialog.destroy())
    
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
    
    def cleanup_tooltips(self):
        """Clean up any lingering tooltips when switching tabs"""
        # Clean up any non-ADP tooltips (ADP tooltips have been removed)
        for widget in self.winfo_children():
            if hasattr(widget, '_tooltip'):
                try:
                    widget._tooltip.destroy()
                except:
                    pass
                delattr(widget, '_tooltip')
    
    def _create_team_logo_cell(self, row, player, bg, select_row):
        """Create a cell with team logo"""
        frame = tk.Frame(row, bg=bg, width=45)
        frame.pack(side='left', fill='y')
        frame.pack_propagate(False)
        frame.bind('<Button-1>', select_row)
        
        if player.team and self.image_service:
            # Create logo label
            logo_label = tk.Label(frame, bg=bg)
            logo_label.pack(expand=True)
            
            # Load team logo asynchronously
            team_code = player.team.lower()
            logo_path = os.path.join(os.path.dirname(__file__), '..', '..', 'assets', 'team_logos', f'{team_code}.png')
            
            if os.path.exists(logo_path):
                try:
                    # Load and resize image
                    from PIL import Image, ImageTk
                    img = Image.open(logo_path)
                    img = img.resize((20, 20), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    
                    # Keep reference to prevent garbage collection
                    logo_label.image = photo
                    logo_label.config(image=photo)
                except Exception as e:
                    # Fallback to text
                    logo_label.config(text=player.team, fg=DARK_THEME['text_secondary'], font=(DARK_THEME['font_family'], 9))
            else:
                # Fallback to text if logo not found
                logo_label.config(text=player.team, fg=DARK_THEME['text_secondary'], font=(DARK_THEME['font_family'], 9))
        else:
            # No team
            label = tk.Label(frame, text='-', bg=bg, fg=DARK_THEME['text_secondary'], font=(DARK_THEME['font_family'], 9))
            label.pack(expand=True)
        
        frame._field_type = 'team'
        return frame
    
    def reset_all_adp(self):
        """Reset all custom ADP values"""
        # Ask for confirmation
        result = messagebox.askyesno(
            "Reset ADP Values",
            "Are you sure you want to reset all custom ADP values to defaults?",
            parent=self.winfo_toplevel()
        )
        
        if result:
            # Clear all custom ADP values
            self.custom_adp_manager.clear_all_custom_adp()
            
            # Reload player data to get original ADP values
            from ..utils import generate_mock_players
            original_players = generate_mock_players()
            
            # Create a map of original ADP values
            original_adp = {p.player_id: p.adp for p in original_players if hasattr(p, 'player_id')}
            
            # Reset ADP values for all current players
            for player in self.all_players:
                if hasattr(player, 'player_id') and player.player_id in original_adp:
                    player.adp = original_adp[player.player_id]
            
            # Refresh the display
            self.update_players(self.all_players, force_refresh=True)
            
            # Notify main app that ADP has changed
            if self.on_adp_change:
                self.on_adp_change()
            
            messagebox.showinfo(
                "ADP Reset",
                "All ADP values have been reset to defaults.",
                parent=self.winfo_toplevel()
            )
    
    def set_watch_list_ref(self, watch_list):
        """Set reference to watch list widget"""
        self.watch_list_ref = watch_list
    
    def update_nfc_adp(self):
        """Fetch and update NFC ADP data"""
        self.nfc_adp_data = self.nfc_adp_fetcher.fetch_nfc_adp()
        if self.nfc_adp_data:
            # Refresh the display
            self.update_players(self.all_players, force_refresh=True)
            return True
        return False
    
    def set_cheat_sheet_ref(self, cheat_sheet):
        """Set reference to cheat sheet page"""
        self.cheat_sheet_ref = cheat_sheet
        # Update the display to show cheat sheet rounds
        if hasattr(self, 'players') and self.players:
            self.update_players(self.players, force_refresh=True)
    
    def update_table_view(self):
        """Update the table view without recreating all rows"""
        # This method updates the display when custom rankings change
        if hasattr(self, 'players') and self.players:
            self.update_players(self.players, force_refresh=True)
    
    def _on_vegas_props_loaded(self):
        """Called when Vegas props finish loading in background"""
        # Schedule UI update on main thread
        if hasattr(self, 'players') and self.players:
            self.after(0, lambda: self.update_players(self.players, force_refresh=True))
    
    def calculate_player_tier(self, player):
        """Calculate player tier based on ADP or VAR"""
        # Use ADP for tier calculation
        if not player.adp:
            return 8  # Lowest tier
        
        adp = player.adp
        if adp <= 12:  # First round
            return 1
        elif adp <= 24:  # Second round
            return 2
        elif adp <= 36:  # Third round
            return 3
        elif adp <= 60:  # Rounds 4-5
            return 4
        elif adp <= 84:  # Rounds 6-7
            return 5
        elif adp <= 120:  # Rounds 8-10
            return 6
        elif adp <= 150:  # Rounds 11-12
            return 7
        else:
            return 8
    
    def calculate_draft_round(self, player):
        """Calculate which round the player is expected to be drafted"""
        # First check if player has a cheat sheet round assignment
        if self.cheat_sheet_ref:
            cheat_sheet_round = self.cheat_sheet_ref.get_player_round(player.player_id)
            if cheat_sheet_round is not None:
                return str(cheat_sheet_round)
        
        # Fall back to ADP-based calculation
        if not player.adp:
            return None
        
        adp = player.adp
        # Assuming 12-team league (12 picks per round)
        round_num = int((adp - 1) / 12) + 1
        
        # Cap at round 15 for display purposes
        if round_num > 15:
            return "15+"
        
        return str(round_num)
    
    def create_tooltip(self, widget, text):
        """Create a tooltip for a widget"""
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            label = tk.Label(
                tooltip,
                text=text,
                bg=DARK_THEME['bg_tertiary'],
                fg=DARK_THEME['text_primary'],
                font=(DARK_THEME['font_family'], 9),
                padx=5,
                pady=2,
                relief='solid',
                borderwidth=1
            )
            label.pack()
            widget._tooltip = tooltip
        
        def on_leave(event):
            if hasattr(widget, '_tooltip'):
                widget._tooltip.destroy()
                del widget._tooltip
        
        widget.bind('<Enter>', on_enter)
        widget.bind('<Leave>', on_leave)

    def create_suggested_picks_section(self):
        """Create the suggested picks section at the top"""
        self.suggested_frame = StyledFrame(self, bg_type="tertiary")
        self.suggested_frame.pack(fill="x", padx=10, pady=(10, 0))
        
        # Title
        title_label = tk.Label(
            self.suggested_frame,
            text="🎯 Suggested Picks",
            bg=DARK_THEME["bg_tertiary"],
            fg=DARK_THEME["text_primary"],
            font=(DARK_THEME["font_family"], 11, "bold")
        )
        title_label.pack(anchor="w", padx=10, pady=(5, 0))
        
        # Container for suggested player cards
        self.suggested_container = tk.Frame(self.suggested_frame, bg=DARK_THEME["bg_tertiary"])
        self.suggested_container.pack(fill="x", padx=10, pady=5)
        
        # Initially hidden
        self.suggested_frame.pack_forget()
    
    def update_suggested_picks(self):
        """Update the suggested picks based on current draft state"""
        if not self.current_pick or not self.user_team:
            self.suggested_frame.pack_forget()
            return
        
        # Clear existing suggestions
        for widget in self.suggested_container.winfo_children():
            widget.destroy()
        
        # Get top 3 suggestions
        suggestions = self.get_draft_suggestions()
        
        if not suggestions:
            self.suggested_frame.pack_forget()
            return
        
        # Show the frame
        self.suggested_frame.pack(fill="x", padx=10, pady=(10, 0), before=self.winfo_children()[1])
        
        # Create mini cards for each suggestion
        for i, (player, reason) in enumerate(suggestions[:3]):
            self.create_suggestion_card(player, reason, i)
    
    def create_suggestion_card(self, player, reason, index):
        """Create a mini card for a suggested player"""
        card = tk.Frame(
            self.suggested_container,
            bg=DARK_THEME["bg_secondary"],
            relief="solid",
            borderwidth=1
        )
        card.pack(side="left", padx=(0, 10), pady=5, fill="x", expand=True)
        
        # Rank indicator
        rank_label = tk.Label(
            card,
            text=f"#{index + 1}",
            bg=DARK_THEME["button_bg"],
            fg="white",
            font=(DARK_THEME["font_family"], 10, "bold"),
            padx=8,
            pady=4
        )
        rank_label.pack(side="left", padx=(5, 0), pady=5)
        
        # Player info
        info_frame = tk.Frame(card, bg=DARK_THEME["bg_secondary"])
        info_frame.pack(side="left", fill="both", expand=True, padx=10, pady=5)
        
        # Name and position
        name_frame = tk.Frame(info_frame, bg=DARK_THEME["bg_secondary"])
        name_frame.pack(anchor="w")
        
        name_label = tk.Label(
            name_frame,
            text=player.format_name(),
            bg=DARK_THEME["bg_secondary"],
            fg=DARK_THEME["text_primary"],
            font=(DARK_THEME["font_family"], 10, "bold")
        )
        name_label.pack(side="left", padx=(0, 5))
        
        pos_bg = get_position_color(player.position)
        pos_label = tk.Label(
            name_frame,
            text=player.position,
            bg=pos_bg,
            fg="white",
            font=(DARK_THEME["font_family"], 8, "bold"),
            padx=6,
            pady=2
        )
        pos_label.pack(side="left")
        
        # Reason
        reason_label = tk.Label(
            info_frame,
            text=reason,
            bg=DARK_THEME["bg_secondary"],
            fg=DARK_THEME["text_secondary"],
            font=(DARK_THEME["font_family"], 9),
            anchor="w"
        )
        reason_label.pack(anchor="w")
        
        # Draft button
        draft_btn = tk.Button(
            card,
            text="DRAFT",
            bg=DARK_THEME["button_bg"],
            fg="white",
            font=(DARK_THEME["font_family"], 9, "bold"),
            bd=0,
            relief="flat",
            padx=12,
            pady=4,
            command=lambda: self.draft_specific_player(player),
            cursor="hand2",
            activebackground=DARK_THEME["button_hover"]
        )
        draft_btn.pack(side="right", padx=10)
        
        # Make entire card clickable
        def on_card_click(e):
            # Find player in list and select
            for i, p in enumerate(self.players):
                if p.player_id == player.player_id:
                    self.select_player(i)
                    break
        
        card.bind("<Button-1>", on_card_click)
        for widget in [rank_label, info_frame, name_label, pos_label, reason_label]:
            widget.bind("<Button-1>", on_card_click)
    
    def get_draft_suggestions(self):
        """Get top 3 draft suggestions with reasons"""
        if not self.players or not self.user_team:
            return []
        
        suggestions = []
        
        # Calculate position needs
        position_counts = {"QB": 0, "RB": 0, "WR": 0, "TE": 0}
        for pos_players in self.user_team.roster.values():
            for p in pos_players:
                if p.position in position_counts:
                    position_counts[p.position] += 1
        
        position_needs = {
            "QB": 2 - position_counts.get("QB", 0),
            "RB": 5 - position_counts.get("RB", 0),
            "WR": 5 - position_counts.get("WR", 0),
            "TE": 2 - position_counts.get("TE", 0)
        }
        
        # Check for elite values in top 10
        for i, player in enumerate(self.players[:10]):
            if player in self.drafted_players:
                continue
            
            reason = None
            score = 0
            
            # Check if falling below ADP
            if player.adp:
                spots_fallen = self.current_pick - player.adp
                if spots_fallen >= 5:
                    reason = f"Elite value\! Falling {int(spots_fallen)} spots"
                    score = 100 + spots_fallen
                elif spots_fallen >= 3:
                    reason = f"Great value - {int(spots_fallen)} spots below ADP"
                    score = 80 + spots_fallen
            
            # Check position need
            if position_needs.get(player.position, 0) > 0:
                if not reason:
                    reason = f"Fills {player.position} need"
                    score = 60 - i
                else:
                    reason += f" + fills {player.position} need"
                    score += 20
            
            # Top player at position
            if i < 3 and not reason:
                reason = f"Best available {player.position}"
                score = 50 - i
            
            if reason:
                suggestions.append((player, reason, score))
        
        # Sort by score and return top 3
        suggestions.sort(key=lambda x: x[2], reverse=True)
        return [(p, r) for p, r, _ in suggestions[:3]]
    
    def set_draft_context(self, current_pick: int, user_team):
        """Set draft context for BPA calculations"""
        self.current_pick = current_pick
        self.user_team = user_team
        # Refresh the display to update position full indicators
        if hasattr(self, 'row_frames') and self.row_frames:
            self._update_position_full_indicators()
        # Don't update suggested picks here - let it be done explicitly when needed
    
    def _update_position_full_indicators(self):
        """Update the color of player names based on position availability"""
        for row in self.row_frames:
            if not hasattr(row, 'player'):
                continue
            
            player = row.player
            is_full = self._is_position_full(player)
            
            # Find the name cell and update its color
            for widget in row.winfo_children():
                if isinstance(widget, tk.Frame):
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Label) and hasattr(child, '_field_type') and child._field_type == 'name':
                            if is_full:
                                child.config(fg='#FF5E5B')  # Red for full positions
                            else:
                                child.config(fg=DARK_THEME['text_primary'])  # Normal color
                            break

    def _is_position_full(self, player):
        """Check if the user's team is full at this player's position"""
        if not self.user_team:
            return False
        
        position = player.position.upper()
        
        # Get roster limits from config
        import config
        
        # Count total players drafted so far
        total_drafted = sum(len(players) for players in self.user_team.roster.values())
        
        # If roster is completely full, everything is full
        max_roster_size = sum(config.roster_spots.values())
        if total_drafted >= max_roster_size:
            return True
        
        # Count how many of this specific position we have across all roster spots
        position_count = 0
        flex_used = 0
        bench_available = config.roster_spots.get('bn', 0) - len(self.user_team.roster.get('bn', []))
        
        # Count position-specific slots
        for spot, players in self.user_team.roster.items():
            if spot == position.lower():
                position_count = len(players)
            elif spot == 'flex':
                # Count how many flex spots are used
                flex_used = len(players)
        
        max_position = config.roster_spots.get(position.lower(), 0)
        max_flex = config.roster_spots.get('flex', 0)
        
        # Debug: Print for QB positions
        if position == 'QB' and position_count >= max_position:
            print(f"DEBUG: QB check - position_count={position_count}, max={max_position}, bench_available={bench_available}")
        
        # Check if position is full
        if position == 'QB':
            # QB can only go in QB spots or bench
            if position_count >= max_position and bench_available <= 0:
                print(f"DEBUG: QB IS FULL - returning True")
                return True
        elif position in ['RB', 'WR', 'TE']:
            # These can go in their position spots, flex, or bench
            # Check if all possible slots are full
            position_slots_full = position_count >= max_position
            flex_slots_available = flex_used < max_flex
            
            if position_slots_full and not flex_slots_available and bench_available <= 0:
                return True
        elif position in ['LB', 'DB']:
            # Defensive players only go to bench
            if bench_available <= 0:
                return True
        
        return False
    
    def calculate_bpa_indicator(self, player, index):
        """Calculate BPA indicator for a player"""
        if not self.current_pick or not player.adp:
            return None
        
        # Calculate how many spots the player has fallen
        # Positive = player falling (value), Negative = reach
        spots_fallen = self.current_pick - player.adp
        
        # Only show indicators for players falling below ADP
        if spots_fallen < 0:
            return None  # Player would be a reach, no value indicator
        
        # Elite value: Top 3 available and falling 5+ spots
        if index < 3 and spots_fallen >= 5:
            return {
                "text": "🔥",
                "bg": "#ff4444",
                "fg": "white",
                "tooltip": f"Elite value\! Falling {int(spots_fallen)} spots below ADP"
            }
        
        # Great value: Falling 3+ spots
        if spots_fallen >= 3:
            return {
                "text": "⭐",
                "bg": "#ffaa00",
                "fg": "white",
                "tooltip": f"Great value\! {int(spots_fallen)} spots below ADP"
            }
        
        # Check position need if we have user team
        if self.user_team and player.position in ["QB", "RB", "WR", "TE"]:
            position_counts = {"QB": 0, "RB": 0, "WR": 0, "TE": 0}
            for pos_players in self.user_team.roster.values():
                for p in pos_players:
                    if p.position in position_counts:
                        position_counts[p.position] += 1
            
            # Check if position is needed
            position_needs = {
                "QB": 2 - position_counts.get("QB", 0),
                "RB": 5 - position_counts.get("RB", 0),
                "WR": 5 - position_counts.get("WR", 0),
                "TE": 2 - position_counts.get("TE", 0)
            }
            
            if position_needs.get(player.position, 0) > 0:
                return {
                    "text": "✓",
                    "bg": "#00aa00",
                    "fg": "white",
                    "tooltip": f"Fills {player.position} need"
                }
        
        return None
