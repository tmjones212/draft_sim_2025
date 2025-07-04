import tkinter as tk
from tkinter import ttk
from typing import Dict
from ..models import Team
from .theme import DARK_THEME, get_position_color
from .styled_widgets import StyledFrame
from .watch_list import WatchList


class RosterView(StyledFrame):
    def __init__(self, parent, teams: Dict[int, Team], **kwargs):
        super().__init__(parent, bg_type='secondary', **kwargs)
        self.teams = teams
        self.current_team_id = 1  # Start with team 1
        self.current_tab = 'roster'  # 'roster' or 'watch'
        self.watch_list = None
        self.setup_ui()
        
    def setup_ui(self):
        # Tab buttons frame
        tab_frame = StyledFrame(self, bg_type='secondary')
        tab_frame.pack(fill='x', pady=(0, 5))
        
        # Tab buttons
        self.roster_tab_btn = tk.Button(
            tab_frame,
            text="ROSTER",
            bg=DARK_THEME['button_active'],
            fg='white',
            font=(DARK_THEME['font_family'], 10, 'bold'),
            bd=0,
            relief='flat',
            padx=15,
            pady=5,
            command=lambda: self.switch_tab('roster'),
            cursor='hand2'
        )
        self.roster_tab_btn.pack(side='left', padx=(10, 5))
        
        self.watch_tab_btn = tk.Button(
            tab_frame,
            text="WATCH LIST",
            bg=DARK_THEME['button_bg'],
            fg='white',
            font=(DARK_THEME['font_family'], 10, 'bold'),
            bd=0,
            relief='flat',
            padx=15,
            pady=5,
            command=lambda: self.switch_tab('watch'),
            cursor='hand2'
        )
        self.watch_tab_btn.pack(side='left')
        
        # Content container
        self.content_container = StyledFrame(self, bg_type='secondary')
        self.content_container.pack(fill='both', expand=True)
        
        # Create roster view
        self.roster_container = StyledFrame(self.content_container, bg_type='secondary')
        self.setup_roster_view()
        
        # Create watch list view
        self.watch_list = WatchList(self.content_container)
        
        # Show roster by default
        self.switch_tab('roster')
    
    def setup_roster_view(self):
        # Header with team selector
        header_frame = StyledFrame(self.roster_container, bg_type='secondary')
        header_frame.pack(fill='x', pady=(0, 5))
        
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
        self.team_selector.pack(side='left', padx=(10, 0))
        self.team_selector.bind('<<ComboboxSelected>>', self.on_team_change)
        
        # Roster container with scroll
        roster_content = StyledFrame(self.roster_container, bg_type='tertiary')
        roster_content.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Canvas for scrolling
        canvas = tk.Canvas(
            roster_content,
            bg=DARK_THEME['bg_tertiary'],
            highlightthickness=0
        )
        scrollbar = tk.Scrollbar(
            roster_content,
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
    
    def switch_tab(self, tab):
        self.current_tab = tab
        
        # Update button styles
        if tab == 'roster':
            self.roster_tab_btn.config(bg=DARK_THEME['button_active'])
            self.watch_tab_btn.config(bg=DARK_THEME['button_bg'])
            # Hide watch list, show roster
            self.watch_list.pack_forget()
            self.roster_container.pack(fill='both', expand=True)
        else:  # watch
            self.roster_tab_btn.config(bg=DARK_THEME['button_bg'])
            self.watch_tab_btn.config(bg=DARK_THEME['button_active'])
            # Hide roster, show watch list
            self.roster_container.pack_forget()
            self.watch_list.pack(fill='both', expand=True)
    
    def get_watch_list(self):
        return self.watch_list