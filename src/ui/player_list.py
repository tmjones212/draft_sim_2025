import tkinter as tk
from tkinter import ttk
from typing import List, Optional, Callable
from ..models import Player
from .theme import DARK_THEME, get_position_color
from .styled_widgets import StyledFrame


class PlayerList(StyledFrame):
    def __init__(self, parent, on_select: Optional[Callable] = None, **kwargs):
        super().__init__(parent, bg_type='secondary', **kwargs)
        self.on_select = on_select
        self.players: List[Player] = []
        self.selected_index = None
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
        
        # Position filter buttons (future enhancement)
        filter_frame = StyledFrame(header_frame, bg_type='secondary')
        filter_frame.pack(side='right')
        
        # Horizontal scrollable container
        scroll_container = StyledFrame(container, bg_type='secondary')
        scroll_container.pack(fill='both', expand=True)
        
        # Canvas for horizontal scrolling
        self.canvas = tk.Canvas(
            scroll_container,
            bg=DARK_THEME['bg_secondary'],
            highlightthickness=0,
            height=180
        )
        h_scrollbar = tk.Scrollbar(
            scroll_container,
            orient='horizontal',
            command=self.canvas.xview,
            bg=DARK_THEME['bg_tertiary'],
            troughcolor=DARK_THEME['bg_secondary']
        )
        
        self.scrollable_frame = StyledFrame(self.canvas, bg_type='secondary')
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(xscrollcommand=h_scrollbar.set)
        
        self.canvas.pack(side="top", fill="both", expand=True)
        h_scrollbar.pack(side="bottom", fill="x")
        
        # Player cards container
        self.player_cards = []
    
    def update_players(self, players: List[Player], limit: int = 30):
        self.players = players[:limit]
        self.selected_index = None
        
        # Clear existing player cards
        for card in self.player_cards:
            card.destroy()
        self.player_cards.clear()
        
        # Create new player cards in a horizontal layout
        for i, player in enumerate(self.players):
            card = self.create_player_card(i, player)
            card.pack(side='left', padx=5, pady=10)
            self.player_cards.append(card)
    
    def create_player_card(self, index: int, player: Player) -> tk.Frame:
        # Player card container - vertical layout
        card = StyledFrame(
            self.scrollable_frame,
            bg_type='tertiary',
            relief='flat',
            width=130,
            height=140
        )
        card.pack_propagate(False)
        
        # Make card clickable
        def on_click(event):
            self.select_player(index)
        
        card.bind("<Button-1>", on_click)
        
        # Inner container with padding
        inner = StyledFrame(card, bg_type='tertiary')
        inner.pack(fill='both', expand=True, padx=10, pady=10)
        inner.bind("<Button-1>", on_click)
        
        # Rank at top
        rank_label = tk.Label(
            inner,
            text=f"#{player.rank}",
            bg=DARK_THEME['bg_tertiary'],
            fg=DARK_THEME['text_muted'],
            font=(DARK_THEME['font_family'], 16, 'bold')
        )
        rank_label.pack()
        rank_label.bind("<Button-1>", on_click)
        
        # Position badge
        pos_frame = tk.Frame(
            inner,
            bg=get_position_color(player.position),
            padx=8,
            pady=3
        )
        pos_frame.pack(pady=8)
        
        pos_label = tk.Label(
            pos_frame,
            text=player.position,
            bg=get_position_color(player.position),
            fg='white',
            font=(DARK_THEME['font_family'], 10, 'bold')
        )
        pos_label.pack()
        
        # Player name
        name_label = tk.Label(
            inner,
            text=player.name,
            bg=DARK_THEME['bg_tertiary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10),
            wraplength=110
        )
        name_label.pack(fill='x')
        name_label.bind("<Button-1>", on_click)
        
        # ADP/Value info (placeholder)
        value_label = tk.Label(
            inner,
            text=f"ADP: {player.adp}",
            bg=DARK_THEME['bg_tertiary'],
            fg=DARK_THEME['text_muted'],
            font=(DARK_THEME['font_family'], 9)
        )
        value_label.pack(pady=(5, 0))
        value_label.bind("<Button-1>", on_click)
        
        return card
    
    def select_player(self, index: int):
        # Deselect previous
        if self.selected_index is not None and self.selected_index < len(self.player_cards):
            self.player_cards[self.selected_index].config(
                bg=DARK_THEME['bg_tertiary'],
                relief='flat',
                borderwidth=0
            )
        
        # Select new
        self.selected_index = index
        if index < len(self.player_cards):
            self.player_cards[index].config(
                bg=DARK_THEME['current_pick'],
                relief='solid',
                borderwidth=2
            )
        
        # Callback
        if self.on_select and index < len(self.players):
            self.on_select(self.players[index])
    
    def get_selected_player(self) -> Optional[Player]:
        if self.selected_index is not None and self.selected_index < len(self.players):
            return self.players[self.selected_index]
        return None