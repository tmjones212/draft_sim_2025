import tkinter as tk
from tkinter import ttk
from typing import List, Optional, Callable
from PIL import Image, ImageTk
import requests
from io import BytesIO
from ..models import Player
from .theme import DARK_THEME, get_position_color
from .styled_widgets import StyledFrame
from ..utils.player_extensions import get_player_image_url


class PlayerList(StyledFrame):
    def __init__(self, parent, on_select: Optional[Callable] = None, on_draft: Optional[Callable] = None, **kwargs):
        super().__init__(parent, bg_type='secondary', **kwargs)
        self.on_select = on_select
        self.on_draft = on_draft
        self.players: List[Player] = []
        self.selected_index = None
        self.image_cache = {}  # Cache loaded images
        self.player_cards = []
        self.draft_enabled = False
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
            height=200
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
    
    def remove_player_card(self, index: int):
        """Remove a specific player card without refreshing all players"""
        if 0 <= index < len(self.player_cards):
            self.player_cards[index].destroy()
            self.player_cards.pop(index)
            self.players.pop(index)
            
            # No need to update indices anymore since we use player objects
    
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
        
        # Remove each player
        for index in indices_to_remove:
            if 0 <= index < len(self.player_cards):
                self.player_cards[index].destroy()
                self.player_cards.pop(index)
                self.players.pop(index)
        
        # No need to update indices anymore since we use player objects
    
    def create_player_card(self, index: int, player: Player) -> tk.Frame:
        # Player card container - vertical layout
        card = StyledFrame(
            self.scrollable_frame,
            bg_type='tertiary',
            relief='flat',
            width=130,
            height=180  # Adjusted for 40x40 image
        )
        card.pack_propagate(False)
        
        # Make card clickable and double-clickable
        def on_click(event):
            self.select_player(index)
        
        def on_double_click(event):
            self.select_player(index)
            if self.on_draft:
                self.on_draft()
        
        card.bind("<Button-1>", on_click)
        card.bind("<Double-Button-1>", on_double_click)
        
        # Inner container with padding
        inner = StyledFrame(card, bg_type='tertiary')
        inner.pack(fill='both', expand=True, padx=10, pady=8)
        inner.bind("<Button-1>", on_click)
        inner.bind("<Double-Button-1>", on_double_click)
        
        # Player image placeholder
        image_label = None
        if player.player_id:
            # Check cache first
            if player.player_id in self.image_cache:
                photo = self.image_cache[player.player_id]
                image_label = tk.Label(
                    inner,
                    image=photo,
                    bg=DARK_THEME['bg_tertiary']
                )
                image_label.image = photo  # Keep a reference
                image_label.pack(pady=(0, 5))
                image_label.bind("<Button-1>", lambda e: on_click(e))
            else:
                # Create placeholder for image
                image_label = tk.Label(
                    inner,
                    text="",
                    bg=DARK_THEME['bg_tertiary'],
                    height=3,
                    width=5
                )
                image_label.pack(pady=(0, 5))
                image_label.bind("<Button-1>", lambda e: on_click(e))
                # Schedule image loading
                self.after(1, lambda pid=player.player_id, lbl=image_label: self._load_player_image(pid, lbl))
        
        # Rank at top
        rank_label = tk.Label(
            inner,
            text=f"#{player.rank}",
            bg=DARK_THEME['bg_tertiary'],
            fg=DARK_THEME['text_muted'],
            font=(DARK_THEME['font_family'], 14, 'bold')
        )
        rank_label.pack()
        rank_label.bind("<Button-1>", lambda e: on_click(e))
        
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
        name_label.bind("<Button-1>", lambda e: on_click(e))
        
        # Draft button
        if self.on_draft:
            draft_btn = tk.Button(
                inner,
                text="DRAFT",
                bg=DARK_THEME['button_active'],
                fg='white',
                font=(DARK_THEME['font_family'], 8, 'bold'),
                relief='flat',
                cursor='hand2',
                command=lambda p=player: self.draft_specific_player(p),
                state='normal' if self.draft_enabled else 'disabled'
            )
            draft_btn.pack(pady=(5, 0))
            
            # Hover effect
            draft_btn.bind('<Enter>', lambda e: draft_btn.config(bg='#2ecc71'))
            draft_btn.bind('<Leave>', lambda e: draft_btn.config(bg=DARK_THEME['button_active']))
        
        # Remove ADP label if draft button is shown
        if not self.on_draft:
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
    
    def _load_player_image(self, player_id, image_label=None):
        """Load player image asynchronously"""
        if player_id not in self.image_cache:
            try:
                image_url = get_player_image_url(player_id)
                response = requests.get(image_url, timeout=2)
                if response.status_code == 200:
                    img = Image.open(BytesIO(response.content))
                    # Resize image to consistent 40x40 size
                    img = img.resize((40, 40), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    # Cache it
                    self.image_cache[player_id] = photo
                    
                    # If image_label is provided, update it
                    if image_label and image_label.winfo_exists():
                        image_label.configure(image=photo, height=40, width=40)
                        image_label.image = photo
            except:
                pass
    
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
    
    def set_draft_enabled(self, enabled: bool):
        """Enable or disable all draft buttons"""
        self.draft_enabled = enabled
        # Update all existing draft buttons
        for card in self.player_cards:
            # Find the draft button in the card's children
            for widget in card.winfo_children():
                if isinstance(widget, tk.Frame):  # Inner frame
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Button) and child.cget('text') == 'DRAFT':
                            child.config(state='normal' if enabled else 'disabled')