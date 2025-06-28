import tkinter as tk
from tkinter import ttk
from typing import Dict
from ..models import Team
from .theme import DARK_THEME, get_position_color
from .styled_widgets import StyledFrame


class RosterView(StyledFrame):
    def __init__(self, parent, teams: Dict[int, Team], **kwargs):
        super().__init__(parent, bg_type='secondary', **kwargs)
        self.teams = teams
        self.current_team_id = 1  # Start with team 1
        self.setup_ui()
        
    def setup_ui(self):
        # Header with team selector
        header_frame = StyledFrame(self, bg_type='secondary')
        header_frame.pack(fill='x', pady=(0, 5))
        
        # Title
        title = tk.Label(
            header_frame,
            text="ROSTER",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 10, 'bold')
        )
        title.pack(side='left', padx=(10, 20))
        
        # Team selector dropdown
        self.team_var = tk.StringVar(value="Team 1")
        team_names = [f"Team {i}" for i in range(1, len(self.teams) + 1)]
        
        self.team_selector = ttk.Combobox(
            header_frame,
            textvariable=self.team_var,
            values=team_names,
            state='readonly',
            width=10,
            font=(DARK_THEME['font_family'], 9)
        )
        self.team_selector.pack(side='left')
        self.team_selector.bind('<<ComboboxSelected>>', self.on_team_change)
        
        # Roster container with scroll
        roster_container = StyledFrame(self, bg_type='tertiary')
        roster_container.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Canvas for scrolling
        canvas = tk.Canvas(
            roster_container,
            bg=DARK_THEME['bg_tertiary'],
            highlightthickness=0
        )
        scrollbar = tk.Scrollbar(
            roster_container,
            orient='vertical',
            command=canvas.yview,
            bg=DARK_THEME['bg_secondary'],
            troughcolor=DARK_THEME['bg_tertiary']
        )
        
        self.roster_frame = StyledFrame(canvas, bg_type='tertiary')
        self.roster_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.roster_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Initial display
        self.update_roster_display()
    
    def on_team_change(self, event=None):
        team_name = self.team_var.get()
        self.current_team_id = int(team_name.split()[1])
        self.update_roster_display()
    
    def update_all_rosters(self):
        # Just update the current team's display
        self.update_roster_display()
    
    def update_roster_display(self):
        # Clear existing widgets
        for widget in self.roster_frame.winfo_children():
            widget.destroy()
        
        team = self.teams[self.current_team_id]
        roster = team.get_roster_summary()
        
        # Compact position display
        positions = [
            ("QB", "qb"),
            ("RB", "rb"),
            ("WR", "wr"),
            ("TE", "te"),
            ("FLEX", "flex"),
            ("BN", "bn")
        ]
        
        for display_name, pos_key in positions:
            # Position section
            pos_section = StyledFrame(self.roster_frame, bg_type='tertiary')
            pos_section.pack(fill='x', padx=5, pady=(5, 0))
            
            # Position header with count
            pos_header = StyledFrame(pos_section, bg_type='tertiary')
            pos_header.pack(fill='x')
            
            filled = len(roster[pos_key])
            total = team.roster_spots[pos_key]
            
            pos_label = tk.Label(
                pos_header,
                text=f"{display_name} ({filled}/{total})",
                bg=DARK_THEME['bg_tertiary'],
                fg=DARK_THEME['text_muted'],
                font=(DARK_THEME['font_family'], 9, 'bold')
            )
            pos_label.pack(side='left')
            
            # Players grid (2 columns for compact display)
            players_frame = StyledFrame(pos_section, bg_type='tertiary')
            players_frame.pack(fill='x', padx=(10, 0))
            
            # Show players
            for i, player in enumerate(roster[pos_key]):
                row = i // 2
                col = i % 2
                
                player_label = tk.Label(
                    players_frame,
                    text=f"• {player.name[:15]}",  # Truncate long names
                    bg=DARK_THEME['bg_tertiary'],
                    fg=DARK_THEME['text_primary'],
                    font=(DARK_THEME['font_family'], 8),
                    anchor='w'
                )
                player_label.grid(row=row, column=col, sticky='w', padx=(0, 10))
            
            # Show empty slots
            empty_count = total - filled
            if empty_count > 0:
                start_idx = filled
                for i in range(empty_count):
                    idx = start_idx + i
                    row = idx // 2
                    col = idx % 2
                    
                    empty_label = tk.Label(
                        players_frame,
                        text="• --",
                        bg=DARK_THEME['bg_tertiary'],
                        fg=DARK_THEME['text_muted'],
                        font=(DARK_THEME['font_family'], 8),
                        anchor='w'
                    )
                    empty_label.grid(row=row, column=col, sticky='w', padx=(0, 10))