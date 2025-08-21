import tkinter as tk
from tkinter import ttk
from typing import Dict, List
from ..models import Team, Player
from .theme import DARK_THEME, get_position_color
from .styled_widgets import StyledFrame


class DraftStatus(StyledFrame):
    def __init__(self, parent, teams: Dict[int, Team], **kwargs):
        super().__init__(parent, bg_type='secondary', **kwargs)
        self.teams = teams
        self.all_players = []
        self.setup_ui()
        
    def setup_ui(self):
        # Main container
        main_frame = StyledFrame(self, bg_type='secondary')
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Title
        title_label = tk.Label(
            main_frame,
            text="DRAFT STATUS",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 14, 'bold')
        )
        title_label.pack(pady=(0, 10))
        
        # Create two sections: Team Position Counts and Overall Position Totals
        sections_frame = StyledFrame(main_frame, bg_type='secondary')
        sections_frame.pack(fill='both', expand=True)
        
        # Left section - Team Position Counts
        left_frame = StyledFrame(sections_frame, bg_type='tertiary')
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 5))
        
        left_title = tk.Label(
            left_frame,
            text="Team Position Counts",
            bg=DARK_THEME['bg_tertiary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 11, 'bold')
        )
        left_title.pack(pady=5)
        
        # Create team position table
        self.create_team_table(left_frame)
        
        # Right section - Overall Position Totals
        right_frame = StyledFrame(sections_frame, bg_type='tertiary')
        right_frame.pack(side='right', fill='both', expand=True, padx=(5, 0))
        
        right_title = tk.Label(
            right_frame,
            text="Overall Position Totals",
            bg=DARK_THEME['bg_tertiary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 11, 'bold')
        )
        right_title.pack(pady=5)
        
        # Create overall position table
        self.create_overall_table(right_frame)
        
    def create_team_table(self, parent):
        # Create scrollable frame
        canvas_frame = StyledFrame(parent, bg_type='tertiary')
        canvas_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        canvas = tk.Canvas(
            canvas_frame,
            bg=DARK_THEME['bg_tertiary'],
            highlightthickness=0
        )
        scrollbar = tk.Scrollbar(canvas_frame, orient='vertical', command=canvas.yview)
        
        self.team_frame = StyledFrame(canvas, bg_type='tertiary')
        canvas_window = canvas.create_window((0, 0), window=self.team_frame, anchor='nw')
        
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Configure canvas scrolling
        def configure_scroll(event=None):
            canvas.configure(scrollregion=canvas.bbox('all'))
            canvas_width = event.width if event else canvas.winfo_width()
            canvas.itemconfig(canvas_window, width=canvas_width)
        
        self.team_frame.bind('<Configure>', configure_scroll)
        canvas.bind('<Configure>', configure_scroll)
        
        # Header
        header_frame = StyledFrame(self.team_frame, bg_type='tertiary')
        header_frame.pack(fill='x', padx=2, pady=2)
        
        # Column headers
        headers = ['Team', 'QB', 'RB', 'WR', 'TE', 'FLEX', 'LB', 'DB', 'K', 'DST', 'Total']
        col_widths = [100, 40, 40, 40, 40, 50, 40, 40, 40, 45, 50]
        
        for header, width in zip(headers, col_widths):
            label = tk.Label(
                header_frame,
                text=header,
                bg=DARK_THEME['bg_tertiary'],
                fg=DARK_THEME['text_secondary'],
                font=(DARK_THEME['font_family'], 9, 'bold'),
                width=width//8,
                anchor='center'
            )
            label.pack(side='left', padx=1)
        
        # Store team rows for updates
        self.team_rows = {}
        
    def create_overall_table(self, parent):
        # Create frame for overall stats
        self.overall_frame = StyledFrame(parent, bg_type='tertiary')
        self.overall_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Store overall labels for updates
        self.overall_labels = {}
        
    def update_status(self, all_players: List[Player]):
        """Update the draft status display"""
        self.all_players = all_players
        
        # Clear existing team rows
        for row in self.team_rows.values():
            row.destroy()
        self.team_rows.clear()
        
        # Count positions for each team
        team_positions = {}
        overall_positions = {'QB': 0, 'RB': 0, 'WR': 0, 'TE': 0, 'FLEX': 0, 
                            'LB': 0, 'DB': 0, 'K': 0, 'DST': 0}
        
        for team_id, team in self.teams.items():
            team_positions[team_id] = {'QB': 0, 'RB': 0, 'WR': 0, 'TE': 0, 
                                       'FLEX': 0, 'LB': 0, 'DB': 0, 'K': 0, 'DST': 0}
            
            for player in team.roster:
                pos = player.position
                if pos in team_positions[team_id]:
                    team_positions[team_id][pos] += 1
                    overall_positions[pos] += 1
                # Handle FLEX (RB/WR/TE can be FLEX)
                elif pos in ['RB', 'WR', 'TE']:
                    # Count as FLEX if main position slots are filled
                    # This is simplified - you may want more complex logic
                    if pos == 'RB' and team_positions[team_id]['RB'] >= 2:
                        team_positions[team_id]['FLEX'] += 1
                    elif pos == 'WR' and team_positions[team_id]['WR'] >= 3:
                        team_positions[team_id]['FLEX'] += 1
                    elif pos == 'TE' and team_positions[team_id]['TE'] >= 1:
                        team_positions[team_id]['FLEX'] += 1
        
        # Update team table
        for team_id, team in self.teams.items():
            row_frame = StyledFrame(self.team_frame, bg_type='tertiary')
            row_frame.pack(fill='x', padx=2, pady=1)
            
            # Alternate row colors
            if team_id % 2 == 0:
                row_bg = DARK_THEME['bg_secondary']
            else:
                row_bg = DARK_THEME['bg_tertiary']
            
            row_frame.configure(bg=row_bg)
            
            # Team name
            name_label = tk.Label(
                row_frame,
                text=team.name,
                bg=row_bg,
                fg=DARK_THEME['text_primary'],
                font=(DARK_THEME['font_family'], 9),
                width=12,
                anchor='w'
            )
            name_label.pack(side='left', padx=1)
            
            # Position counts
            positions = ['QB', 'RB', 'WR', 'TE', 'FLEX', 'LB', 'DB', 'K', 'DST']
            for pos in positions:
                count = team_positions[team_id][pos]
                
                # Color code based on roster requirements
                color = DARK_THEME['text_primary']
                if pos == 'QB' and count < 1:
                    color = '#FF6B6B'  # Red for needed
                elif pos == 'RB' and count < 2:
                    color = '#FF6B6B'
                elif pos == 'WR' and count < 3:
                    color = '#FF6B6B'
                elif pos == 'TE' and count < 1:
                    color = '#FF6B6B'
                elif count > 0:
                    color = '#4ECDC4'  # Teal for filled
                
                count_label = tk.Label(
                    row_frame,
                    text=str(count),
                    bg=row_bg,
                    fg=color,
                    font=(DARK_THEME['font_family'], 9, 'bold'),
                    width=5,
                    anchor='center'
                )
                count_label.pack(side='left', padx=1)
            
            # Total
            total = sum(team_positions[team_id].values())
            total_label = tk.Label(
                row_frame,
                text=str(total),
                bg=row_bg,
                fg=DARK_THEME['text_primary'],
                font=(DARK_THEME['font_family'], 9, 'bold'),
                width=6,
                anchor='center'
            )
            total_label.pack(side='left', padx=1)
            
            self.team_rows[team_id] = row_frame
        
        # Update overall table
        for widget in self.overall_frame.winfo_children():
            widget.destroy()
        
        # Overall stats grid
        positions = ['QB', 'RB', 'WR', 'TE', 'FLEX', 'LB', 'DB', 'K', 'DST']
        
        for i, pos in enumerate(positions):
            row = i // 3
            col = i % 3
            
            pos_frame = StyledFrame(self.overall_frame, bg_type='secondary')
            pos_frame.grid(row=row, column=col, padx=5, pady=5, sticky='ew')
            
            # Position label with color
            pos_color = get_position_color(pos)
            pos_label = tk.Label(
                pos_frame,
                text=pos,
                bg=DARK_THEME['bg_secondary'],
                fg=pos_color,
                font=(DARK_THEME['font_family'], 11, 'bold'),
                width=8
            )
            pos_label.pack(side='left', padx=5)
            
            # Count
            count = overall_positions[pos]
            count_label = tk.Label(
                pos_frame,
                text=f"{count} drafted",
                bg=DARK_THEME['bg_secondary'],
                fg=DARK_THEME['text_primary'],
                font=(DARK_THEME['font_family'], 10)
            )
            count_label.pack(side='left')
            
            # Available count
            available = len([p for p in self.all_players 
                           if p.position == pos and not p.drafted])
            avail_label = tk.Label(
                pos_frame,
                text=f"({available} left)",
                bg=DARK_THEME['bg_secondary'],
                fg=DARK_THEME['text_secondary'],
                font=(DARK_THEME['font_family'], 9)
            )
            avail_label.pack(side='left', padx=(5, 0))
        
        # Configure grid weights
        for i in range(3):
            self.overall_frame.grid_columnconfigure(i, weight=1)