import tkinter as tk
from typing import List, Set
from ..models import Player
from .theme import DARK_THEME, get_position_color
from .styled_widgets import StyledFrame


class WatchList(StyledFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg_type='secondary', **kwargs)
        self.watched_players: List[Player] = []
        self.watched_player_ids: Set[int] = set()
        self.setup_ui()
        
    def setup_ui(self):
        # Header
        header_frame = StyledFrame(self, bg_type='secondary')
        header_frame.pack(fill='x', pady=(0, 5))
        
        title = tk.Label(
            header_frame,
            text="WATCH LIST",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 10, 'bold')
        )
        title.pack(side='left', padx=(10, 20))
        
        # Clear button
        clear_button = tk.Button(
            header_frame,
            text="Clear All",
            bg=DARK_THEME['button_bg'],
            fg='white',
            font=(DARK_THEME['font_family'], 8),
            bd=0,
            relief='flat',
            padx=8,
            pady=2,
            command=self.clear_all,
            cursor='hand2'
        )
        clear_button.pack(side='right', padx=10)
        
        # Watch list container with scroll
        list_container = StyledFrame(self, bg_type='tertiary')
        list_container.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Canvas for scrolling
        canvas = tk.Canvas(
            list_container,
            bg=DARK_THEME['bg_tertiary'],
            highlightthickness=0
        )
        scrollbar = tk.Scrollbar(
            list_container,
            orient='vertical',
            command=canvas.yview,
            bg=DARK_THEME['bg_secondary'],
            troughcolor=DARK_THEME['bg_tertiary']
        )
        
        self.list_frame = StyledFrame(canvas, bg_type='tertiary')
        self.list_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.list_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Enable drop
        self.configure_drop_target()
        
        # Initial display
        self.update_display()
    
    def configure_drop_target(self):
        # Make this widget a drop target
        self.bind("<Button-1>", lambda e: self.focus_set())
        
    def add_player(self, player: Player):
        if player.player_id not in self.watched_player_ids:
            self.watched_players.append(player)
            self.watched_player_ids.add(player.player_id)
            self.update_display()
    
    def remove_player(self, player: Player):
        if player.player_id in self.watched_player_ids:
            self.watched_players = [p for p in self.watched_players if p.player_id != player.player_id]
            self.watched_player_ids.remove(player.player_id)
            self.update_display()
            
            # Update player list star icons if reference exists
            if hasattr(self, 'player_list_ref') and self.player_list_ref:
                self.player_list_ref.watched_player_ids.discard(player.player_id)
                self.player_list_ref._update_star_icons()
    
    def clear_all(self):
        self.watched_players.clear()
        self.watched_player_ids.clear()
        self.update_display()
        
        # Update player list star icons if reference exists
        if hasattr(self, 'player_list_ref') and self.player_list_ref:
            self.player_list_ref.watched_player_ids.clear()
            self.player_list_ref._update_star_icons()
    
    def remove_drafted_player(self, player_id: int):
        if player_id in self.watched_player_ids:
            self.watched_players = [p for p in self.watched_players if p.player_id != player_id]
            self.watched_player_ids.remove(player_id)
            self.update_display()
            
            # Update player list star icons if reference exists
            if hasattr(self, 'player_list_ref') and self.player_list_ref:
                self.player_list_ref.watched_player_ids.discard(player_id)
                self.player_list_ref._update_star_icons()
    
    def update_display(self):
        # Clear existing widgets
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        
        if not self.watched_players:
            # Show empty message
            empty_label = tk.Label(
                self.list_frame,
                text="Drag players here to watch",
                bg=DARK_THEME['bg_tertiary'],
                fg=DARK_THEME['text_muted'],
                font=(DARK_THEME['font_family'], 9, 'italic')
            )
            empty_label.pack(pady=20)
            return
        
        # Display watched players
        for player in self.watched_players:
            player_frame = StyledFrame(self.list_frame, bg_type='secondary')
            player_frame.pack(fill='x', padx=3, pady=2)
            
            # Player info container
            info_frame = StyledFrame(player_frame, bg_type='secondary')
            info_frame.pack(side='left', fill='x', expand=True)
            
            # Position badge
            pos_label = tk.Label(
                info_frame,
                text=player.position,
                bg=get_position_color(player.position),
                fg='white',
                font=(DARK_THEME['font_family'], 8, 'bold'),
                width=3
            )
            pos_label.pack(side='left', padx=(5, 10))
            
            # Player name
            name_label = tk.Label(
                info_frame,
                text=player.formatted_name[:20],  # Truncate long names
                bg=DARK_THEME['bg_secondary'],
                fg=DARK_THEME['text_primary'],
                font=(DARK_THEME['font_family'], 9),
                anchor='w'
            )
            name_label.pack(side='left', fill='x', expand=True)
            
            # ADP
            adp_label = tk.Label(
                info_frame,
                text=f"ADP: {player.adp:.1f}",
                bg=DARK_THEME['bg_secondary'],
                fg=DARK_THEME['text_muted'],
                font=(DARK_THEME['font_family'], 8)
            )
            adp_label.pack(side='left', padx=(0, 5))
            
            # Remove button
            remove_btn = tk.Button(
                player_frame,
                text="✕",
                bg=DARK_THEME['button_bg'],
                fg='white',
                font=(DARK_THEME['font_family'], 8),
                bd=0,
                relief='flat',
                padx=5,
                pady=1,
                command=lambda p=player: self.remove_player(p),
                cursor='hand2'
            )
            remove_btn.pack(side='right', padx=5)
    
    def set_player_list_ref(self, player_list):
        """Set reference to player list widget for bidirectional updates"""
        self.player_list_ref = player_list