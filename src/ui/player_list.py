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
        
        # Sort controls
        sort_frame = StyledFrame(header_frame, bg_type='secondary')
        sort_frame.pack(side='left', padx=20)
        
        sort_label = tk.Label(
            sort_frame,
            text="Sort:",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 9)
        )
        sort_label.pack(side='left', padx=(0, 5))
        
        # Sort buttons
        self.sort_buttons = {}
        sort_options = [("Rank", "rank"), ("ADP", "adp")]
        
        for label, value in sort_options:
            btn = tk.Button(
                sort_frame,
                text=label,
                bg=DARK_THEME['button_active'] if value == "rank" else DARK_THEME['button_bg'],
                fg='white',
                font=(DARK_THEME['font_family'], 9),
                bd=1,
                relief='solid',
                padx=8,
                pady=2,
                command=lambda v=value: self.sort_players(v),
                cursor='hand2'
            )
            btn.pack(side='left', padx=2)
            self.sort_buttons[value] = btn
        
        # Position filter buttons
        filter_frame = StyledFrame(header_frame, bg_type='secondary')
        filter_frame.pack(side='right')
        
        # Add position filter buttons
        positions = ["ALL", "QB", "RB", "WR", "TE"]
        self.position_buttons = {}
        
        for pos in positions:
            btn = tk.Button(
                filter_frame,
                text=pos,
                bg=DARK_THEME['button_bg'] if pos != "ALL" else DARK_THEME['button_active'],
                fg='white',
                font=(DARK_THEME['font_family'], 9),
                bd=1,
                relief='solid',
                padx=10,
                pady=3,
                command=lambda p=pos: self.filter_by_position(p),
                cursor='hand2'
            )
            btn.pack(side='left', padx=2)
            self.position_buttons[pos] = btn
        
        # Table container
        self.create_table_view(container)
    
    def create_table_view(self, parent):
        """Create the table view for players"""
        self.table_container = StyledFrame(parent, bg_type='secondary')
        self.table_container.pack(fill='both', expand=True)
        
        # Table with scrollbar
        table_scroll_container = StyledFrame(self.table_container, bg_type='secondary')
        table_scroll_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create Treeview for table
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure dark theme for Treeview
        style.configure("Treeview",
                       background=DARK_THEME['bg_tertiary'],
                       foreground=DARK_THEME['text_primary'],
                       fieldbackground=DARK_THEME['bg_tertiary'],
                       borderwidth=0,
                       font=(DARK_THEME['font_family'], 11),
                       rowheight=30)
        style.configure("Treeview.Heading",
                       background=DARK_THEME['bg_secondary'],
                       foreground=DARK_THEME['text_primary'],
                       borderwidth=1,
                       font=(DARK_THEME['font_family'], 11, 'bold'))
        style.map('Treeview', background=[('selected', DARK_THEME['button_active'])])
        
        # Create treeview with columns
        columns = ('rank', 'pos', 'name', 'team', 'adp')
        self.table = ttk.Treeview(table_scroll_container, columns=columns, show='headings', height=20)
        
        # Define column headings and widths
        self.table.heading('rank', text='Rank')
        self.table.heading('pos', text='Pos')
        self.table.heading('name', text='Name')
        self.table.heading('team', text='Team')
        self.table.heading('adp', text='ADP')
        
        self.table.column('rank', width=70, anchor='center')
        self.table.column('pos', width=60, anchor='center')
        self.table.column('name', width=300, anchor='w')
        self.table.column('team', width=80, anchor='center')
        self.table.column('adp', width=80, anchor='center')
        
        # Scrollbar for table
        table_scrollbar = tk.Scrollbar(table_scroll_container, orient='vertical', command=self.table.yview)
        self.table.configure(yscrollcommand=table_scrollbar.set)
        
        self.table.pack(side='left', fill='both', expand=True)
        table_scrollbar.pack(side='right', fill='y')
        
        # Bind double-click to draft
        self.table.bind('<Double-Button-1>', self.on_table_double_click)
        self.table.bind('<<TreeviewSelect>>', self.on_table_select)
        
        # Make headers clickable for sorting
        self.table.heading('rank', text='Rank', command=lambda: self.sort_table_by('rank'))
        self.table.heading('pos', text='Pos', command=lambda: self.sort_table_by('position'))
        self.table.heading('name', text='Name', command=lambda: self.sort_table_by('name'))
        self.table.heading('team', text='Team', command=lambda: self.sort_table_by('team'))
        self.table.heading('adp', text='ADP', command=lambda: self.sort_table_by('adp'))
    
    def update_players(self, players: List[Player], limit: int = 30):
        # Store all players
        self.all_players = players
        
        # Apply position filter
        if self.selected_position == "ALL":
            filtered_players = players
        else:
            filtered_players = [p for p in players if p.position == self.selected_position]
        
        # Apply sorting
        if self.sort_by == "adp":
            # Sort by ADP, putting players without ADP at the end
            filtered_players = sorted(filtered_players, 
                                    key=lambda p: p.adp if p.adp else float('inf'))
        else:  # Default sort by rank
            filtered_players = sorted(filtered_players, key=lambda p: p.rank)
        
        self.players = filtered_players
        self.selected_index = None
        
        # Always update table view
        self.update_table_view()
    
    def remove_player_card(self, index: int):
        """Remove a specific player without refreshing all players"""
        if 0 <= index < len(self.players):
            self.players.pop(index)
            self.update_table_view()
    
    def remove_players(self, players_to_remove: List[Player]):
        """Remove multiple players from the list efficiently"""
        # Find indices of all players to remove
        indices_to_remove = []
        for player in players_to_remove:
            for i, p in enumerate(self.players):
                if p == player:
                    indices_to_remove.append(i)
                    break
        
        # Sort in reverse order so we remove from the end first
        indices_to_remove.sort(reverse=True)
        
        # Remove players and update table
        for index in indices_to_remove:
            if 0 <= index < len(self.players):
                self.players.pop(index)
        self.update_table_view()
    
    def select_player(self, index: int):
        """Select a player by index"""
        self.selected_index = index
        # Update visual selection
        for i, item in enumerate(self.table.get_children()):
            if i == index:
                self.table.selection_set(item)
            else:
                self.table.selection_remove(item)
        
        # Callback
        if self.on_select and index < len(self.players):
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
        
        # Update button appearances
        for pos, btn in self.position_buttons.items():
            if pos == position:
                btn.config(bg=DARK_THEME['button_active'])
            else:
                btn.config(bg=DARK_THEME['button_bg'])
        
        # Refresh the player list with the filter applied
        self.update_players(self.all_players)
    
    def sort_players(self, sort_by: str):
        """Sort players by specified criteria"""
        self.sort_by = sort_by
        
        # Update button appearances
        for key, btn in self.sort_buttons.items():
            if key == sort_by:
                btn.config(bg=DARK_THEME['button_active'])
            else:
                btn.config(bg=DARK_THEME['button_bg'])
        
        # Refresh the player list with the new sort
        self.update_players(self.all_players)
    
    def set_draft_enabled(self, enabled: bool):
        """Enable or disable all draft buttons"""
        self.draft_enabled = enabled
    
    def update_table_view(self):
        """Update the table view with current players"""
        # Clear existing items
        for item in self.table.get_children():
            self.table.delete(item)
        
        # Add players to table
        for i, player in enumerate(self.players):
            values = (
                f"#{player.rank}",
                player.position,
                player.name,
                player.team or '-',
                f"{player.adp:.1f}" if player.adp else '-'
            )
            self.table.insert('', 'end', values=values, tags=(player.position,))
        
        # Apply position colors to tags
        for pos in ['QB', 'RB', 'WR', 'TE']:
            self.table.tag_configure(pos, foreground=get_position_color(pos))
    
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