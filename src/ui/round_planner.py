import tkinter as tk
from tkinter import ttk
from typing import List, Dict, Optional
from ..models import Player
from .theme import DARK_THEME, get_position_color
from .styled_widgets import StyledFrame
from ..services.custom_round_manager import CustomRoundManager


class RoundPlannerView(StyledFrame):
    """View to show players organized by their assigned rounds"""
    
    def __init__(self, parent, players: List[Player] = None, **kwargs):
        super().__init__(parent, bg_type='secondary', **kwargs)
        self.all_players = players or []
        self.custom_round_manager = CustomRoundManager()
        self.round_frames = {}
        
        self._create_ui()
        if self.all_players:
            self.update_players(self.all_players)
    
    def _create_ui(self):
        """Create the round planner UI"""
        # Header
        header_frame = tk.Frame(self, bg=DARK_THEME['bg_secondary'])
        header_frame.pack(fill='x', padx=10, pady=(10, 5))
        
        title_label = tk.Label(
            header_frame,
            text="Draft Round Planner",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 14, 'bold')
        )
        title_label.pack(side='left')
        
        # Info label
        info_label = tk.Label(
            header_frame,
            text="Players you've assigned to specific rounds for draft planning",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 10)
        )
        info_label.pack(side='left', padx=(20, 0))
        
        # Scrollable container
        self.canvas = tk.Canvas(self, bg=DARK_THEME['bg_secondary'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient='vertical', command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=DARK_THEME['bg_secondary'])
        
        self.scrollable_frame.bind(
            '<Configure>',
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all'))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor='nw')
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side='left', fill='both', expand=True, padx=(10, 0))
        scrollbar.pack(side='right', fill='y')
        
        # Bind mousewheel
        self._bind_mousewheel()
    
    def _bind_mousewheel(self):
        """Bind mousewheel events for scrolling"""
        def on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        self.canvas.bind_all("<MouseWheel>", on_mousewheel)
    
    def update_players(self, players: List[Player]):
        """Update the view with new player list"""
        self.all_players = players
        
        # Clear existing round frames
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.round_frames.clear()
        
        # Group players by custom round
        players_by_round: Dict[int, List[Player]] = {}
        
        for player in players:
            custom_round = self.custom_round_manager.get_custom_round(player.player_id)
            if custom_round:
                if custom_round not in players_by_round:
                    players_by_round[custom_round] = []
                players_by_round[custom_round].append(player)
        
        # Create round sections
        for round_num in sorted(players_by_round.keys()):
            self._create_round_section(round_num, players_by_round[round_num])
        
        # If no custom rounds assigned, show empty state
        if not players_by_round:
            empty_label = tk.Label(
                self.scrollable_frame,
                text="No players assigned to rounds yet.\nClick on a player's round tag (Rd column) to assign them.",
                bg=DARK_THEME['bg_secondary'],
                fg=DARK_THEME['text_muted'],
                font=(DARK_THEME['font_family'], 12),
                justify='center'
            )
            empty_label.pack(pady=50)
    
    def _create_round_section(self, round_num: int, players: List[Player]):
        """Create a section for a specific round"""
        # Round header
        header_frame = tk.Frame(self.scrollable_frame, bg=DARK_THEME['bg_tertiary'])
        header_frame.pack(fill='x', pady=(10, 0), padx=5)
        
        # Determine round color
        if round_num <= 3:
            round_color = '#FF5E5B'  # Red
        elif round_num <= 6:
            round_color = '#FFB347'  # Orange
        elif round_num <= 9:
            round_color = '#4ECDC4'  # Teal
        else:
            round_color = '#7B68EE'  # Purple
        
        # Round label
        round_label = tk.Label(
            header_frame,
            text=f"Round {round_num}",
            bg=round_color,
            fg='white',
            font=(DARK_THEME['font_family'], 12, 'bold'),
            padx=10,
            pady=5
        )
        round_label.pack(side='left')
        
        # Player count
        count_label = tk.Label(
            header_frame,
            text=f"{len(players)} players",
            bg=DARK_THEME['bg_tertiary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 10)
        )
        count_label.pack(side='left', padx=(10, 0))
        
        # Players container
        players_frame = tk.Frame(self.scrollable_frame, bg=DARK_THEME['bg_primary'])
        players_frame.pack(fill='x', padx=5, pady=(0, 5))
        
        # Sort players by ADP within round
        sorted_players = sorted(players, key=lambda p: p.adp if p.adp else 999)
        
        # Create player rows
        for i, player in enumerate(sorted_players):
            self._create_player_row(players_frame, player, i)
    
    def _create_player_row(self, parent, player: Player, index: int):
        """Create a row for a player"""
        bg = DARK_THEME['bg_secondary'] if index % 2 == 0 else DARK_THEME['bg_tertiary']
        
        row = tk.Frame(parent, bg=bg, height=35)
        row.pack(fill='x')
        
        # Position badge
        pos_frame = tk.Frame(row, bg=get_position_color(player.position), padx=8, pady=2)
        pos_frame.pack(side='left', padx=(10, 5), pady=5)
        
        pos_label = tk.Label(
            pos_frame,
            text=player.position,
            bg=get_position_color(player.position),
            fg='white',
            font=(DARK_THEME['font_family'], 9, 'bold')
        )
        pos_label.pack()
        
        # Player name
        name_label = tk.Label(
            row,
            text=player.format_name(),
            bg=bg,
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10),
            anchor='w'
        )
        name_label.pack(side='left', padx=5)
        
        # Team
        team_label = tk.Label(
            row,
            text=f"({player.team})" if player.team else "",
            bg=bg,
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 9),
            anchor='w'
        )
        team_label.pack(side='left', padx=(0, 10))
        
        # ADP
        adp_text = f"ADP: {int(player.adp)}" if player.adp else "ADP: -"
        adp_label = tk.Label(
            row,
            text=adp_text,
            bg=bg,
            fg=DARK_THEME['text_accent'],
            font=(DARK_THEME['font_family'], 9)
        )
        adp_label.pack(side='right', padx=10)
        
        # 2024 Points
        points_text = f"{getattr(player, 'points_2024', 0):.1f} pts"
        points_label = tk.Label(
            row,
            text=points_text,
            bg=bg,
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 9)
        )
        points_label.pack(side='right', padx=10)
    
    def refresh(self):
        """Refresh the view with current players"""
        if self.all_players:
            self.update_players(self.all_players)