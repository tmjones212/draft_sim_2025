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
        self.roster_tabs = {}
        self.setup_ui()
        
    def setup_ui(self):
        # Title - smaller
        title_frame = StyledFrame(self, bg_type='secondary')
        title_frame.pack(fill='x', pady=(0, 5))
        
        title = tk.Label(
            title_frame,
            text="ROSTERS",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 10, 'bold')
        )
        title.pack()
        
        # Notebook for teams
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)
        
        # Create tab for each team
        for team_id, team in self.teams.items():
            # Tab frame
            tab_frame = StyledFrame(self.notebook, bg_type='tertiary')
            self.notebook.add(tab_frame, text=team.name)
            
            # Canvas for scrolling
            canvas = tk.Canvas(
                tab_frame,
                bg=DARK_THEME['bg_tertiary'],
                highlightthickness=0
            )
            scrollbar = tk.Scrollbar(
                tab_frame,
                orient='vertical',
                command=canvas.yview,
                bg=DARK_THEME['bg_secondary'],
                troughcolor=DARK_THEME['bg_tertiary']
            )
            
            scrollable_frame = StyledFrame(canvas, bg_type='tertiary')
            scrollable_frame.bind(
                "<Configure>",
                lambda e, canvas=canvas: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            canvas.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
            scrollbar.pack(side="right", fill="y", pady=10)
            
            self.roster_tabs[team_id] = scrollable_frame
    
    def update_all_rosters(self):
        for team_id, roster_frame in self.roster_tabs.items():
            self.update_team_roster(team_id, roster_frame)
    
    def update_team_roster(self, team_id: int, roster_frame: tk.Frame):
        # Clear existing widgets
        for widget in roster_frame.winfo_children():
            widget.destroy()
        
        team = self.teams[team_id]
        roster = team.get_roster_summary()
        
        position_display = {
            "qb": "QB",
            "rb": "RB", 
            "wr": "WR",
            "te": "TE",
            "flex": "FLEX",
            "bn": "BENCH"
        }
        
        for pos, display_name in position_display.items():
            # Position header
            pos_header = StyledFrame(roster_frame, bg_type='tertiary')
            pos_header.pack(fill='x', padx=10, pady=(10, 5))
            
            pos_label = tk.Label(
                pos_header,
                text=display_name,
                bg=DARK_THEME['bg_tertiary'],
                fg=DARK_THEME['text_muted'],
                font=(DARK_THEME['font_family'], 9, 'bold')
            )
            pos_label.pack(side='left')
            
            # Slot count
            filled = len(roster[pos])
            total = team.roster_spots[pos]
            count_label = tk.Label(
                pos_header,
                text=f"{filled}/{total}",
                bg=DARK_THEME['bg_tertiary'],
                fg=DARK_THEME['text_muted'],
                font=(DARK_THEME['font_family'], 10)
            )
            count_label.pack(side='right')
            
            # Players in position
            for player in roster[pos]:
                player_frame = StyledFrame(roster_frame, bg_type='secondary')
                player_frame.pack(fill='x', padx=10, pady=2)
                
                # Player name - smaller font
                name_label = tk.Label(
                    player_frame,
                    text=player.name,
                    bg=DARK_THEME['bg_secondary'],
                    fg=DARK_THEME['text_primary'],
                    font=(DARK_THEME['font_family'], 9),
                    anchor='w'
                )
                name_label.pack(side='left', fill='x', expand=True, padx=5, pady=3)
                
                # Position badge
                pos_badge_frame = tk.Frame(
                    player_frame,
                    bg=get_position_color(player.position),
                    padx=6,
                    pady=2
                )
                pos_badge_frame.pack(side='right', padx=10)
                
                pos_badge = tk.Label(
                    pos_badge_frame,
                    text=player.position,
                    bg=get_position_color(player.position),
                    fg='white',
                    font=(DARK_THEME['font_family'], 9, 'bold')
                )
                pos_badge.pack()
            
            # Empty slots
            empty_slots = team.roster_spots[pos] - len(roster[pos])
            for _ in range(empty_slots):
                empty_frame = StyledFrame(roster_frame, bg_type='secondary')
                empty_frame.pack(fill='x', padx=10, pady=2)
                
                empty_label = tk.Label(
                    empty_frame,
                    text="--",
                    bg=DARK_THEME['bg_secondary'],
                    fg=DARK_THEME['text_muted'],
                    font=(DARK_THEME['font_family'], 9),
                    anchor='w'
                )
                empty_label.pack(side='left', fill='x', expand=True, padx=5, pady=3)