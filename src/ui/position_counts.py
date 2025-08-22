import tkinter as tk
from tkinter import ttk
from typing import Dict, List
from ..models import Team, Player
from ..core import DraftPick
from .theme import DARK_THEME, get_position_color
from .styled_widgets import StyledFrame


class PositionCounts(StyledFrame):
    def __init__(self, parent, teams: Dict[int, Team], **kwargs):
        super().__init__(parent, bg_type='secondary', **kwargs)
        self.teams = teams
        self.draft_results: List[DraftPick] = []
        self.position_order = ['QB', 'RB', 'WR', 'TE']
        self.setup_ui()
        
    def setup_ui(self):
        # Header
        header_frame = StyledFrame(self, bg_type='secondary')
        header_frame.pack(fill='x', pady=(0, 10))
        
        title = tk.Label(
            header_frame,
            text="POSITION COUNTS BY TEAM",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 11, 'bold')
        )
        title.pack(side='left', padx=(10, 20))
        
        # Table container with scrolling
        table_container = StyledFrame(self, bg_type='tertiary')
        table_container.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Canvas for scrolling
        canvas = tk.Canvas(
            table_container,
            bg=DARK_THEME['bg_tertiary'],
            highlightthickness=0
        )
        scrollbar = tk.Scrollbar(
            table_container,
            orient='vertical',
            command=canvas.yview,
            bg=DARK_THEME['bg_secondary'],
            troughcolor=DARK_THEME['bg_tertiary']
        )
        
        # Frame inside canvas for the table
        self.table_frame = StyledFrame(canvas, bg_type='tertiary')
        self.table_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.table_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Initial display
        self.update_display()
    
    def update_draft_results(self, draft_results: List[DraftPick]):
        """Update the position counts based on draft results"""
        self.draft_results = draft_results
        self.update_display()
    
    def get_position_color(self, position, count):
        """Get color for position count based on thresholds"""
        if count == 0:
            return DARK_THEME['text_muted']
        
        # Define problematic thresholds
        thresholds = {
            'QB': {'red': 2},  # 2 or more QBs is red
            'RB': {'red': 4},  # 4 or more RBs is red
            'WR': {'red': 4},  # 4 or more WRs is red
            'TE': {'red': 1}   # Only 1 TE is red (should have 2+)
        }
        
        if position in thresholds:
            if position == 'TE':
                # For TE, red if count is exactly 1 (too few)
                if count == 1:
                    return '#F44336'  # Red
            else:
                # For others, red if count meets or exceeds threshold
                if count >= thresholds[position]['red']:
                    return '#F44336'  # Red
        
        return DARK_THEME['text_primary']  # Default color
    
    def update_display(self):
        """Update the display with current position counts"""
        # Clear existing widgets
        for widget in self.table_frame.winfo_children():
            widget.destroy()
        
        # Calculate position counts for each team
        position_counts = {}
        for team_id, team in self.teams.items():
            position_counts[team_id] = {pos: 0 for pos in self.position_order}
            position_counts[team_id]['total'] = 0
        
        # Count drafted players by position
        for pick in self.draft_results:
            if pick.player and hasattr(pick.player, 'position'):
                pos = pick.player.position
                # Only count QB, RB, WR, TE positions
                if pos in self.position_order:
                    position_counts[pick.team_id][pos] += 1
                    position_counts[pick.team_id]['total'] += 1
        
        # Calculate totals for each position
        position_totals = {pos: 0 for pos in self.position_order}
        grand_total = 0
        
        # Create header row
        header_row = 0
        headers = ['Team'] + self.position_order + ['Total']
        for col, header in enumerate(headers):
            label = tk.Label(
                self.table_frame,
                text=header,
                bg=DARK_THEME['bg_secondary'],
                fg=DARK_THEME['text_primary'],
                font=(DARK_THEME['font_family'], 10, 'bold'),
                padx=10,
                pady=5,
                anchor='w' if col == 0 else 'center'
            )
            label.grid(row=header_row, column=col, sticky='ew')
        
        # Configure column weights
        self.table_frame.grid_columnconfigure(0, weight=2, minsize=120)  # Team column wider
        for col in range(1, len(headers)):
            self.table_frame.grid_columnconfigure(col, weight=1, minsize=50)
        
        # Add rows for each team
        row = 1
        for team_id in sorted(self.teams.keys()):
            team = self.teams[team_id]
            counts = position_counts[team_id]
            
            # Alternate row colors
            row_bg = DARK_THEME['bg_tertiary'] if row % 2 == 1 else DARK_THEME['bg_secondary']
            
            # Team name
            team_label = tk.Label(
                self.table_frame,
                text=team.name,
                bg=row_bg,
                fg=DARK_THEME['text_primary'],
                font=(DARK_THEME['font_family'], 10),
                padx=10,
                pady=3,
                anchor='w'
            )
            team_label.grid(row=row, column=0, sticky='ew')
            
            # Position counts
            col = 1
            for pos in self.position_order:
                count = counts[pos]
                color = self.get_position_color(pos, count)
                
                count_label = tk.Label(
                    self.table_frame,
                    text=str(count) if count > 0 else '-',
                    bg=row_bg,
                    fg=color,
                    font=(DARK_THEME['font_family'], 10, 'bold' if color == '#F44336' else 'normal'),
                    padx=10,
                    pady=3,
                    anchor='center'
                )
                count_label.grid(row=row, column=col, sticky='ew')
                position_totals[pos] += count
                col += 1
            
            # Total
            total_label = tk.Label(
                self.table_frame,
                text=str(counts['total']) if counts['total'] > 0 else '-',
                bg=row_bg,
                fg=DARK_THEME['text_primary'],
                font=(DARK_THEME['font_family'], 10),
                padx=10,
                pady=3,
                anchor='center'
            )
            total_label.grid(row=row, column=col, sticky='ew')
            grand_total += counts['total']
            
            row += 1
        
        # Add separator
        separator_frame = tk.Frame(self.table_frame, bg=DARK_THEME['bg_primary'], height=2)
        separator_frame.grid(row=row, column=0, columnspan=len(headers), sticky='ew', pady=2)
        row += 1
        
        # Add totals row
        total_label = tk.Label(
            self.table_frame,
            text='TOTAL',
            bg=DARK_THEME['bg_hover'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10, 'bold'),
            padx=10,
            pady=5,
            anchor='w'
        )
        total_label.grid(row=row, column=0, sticky='ew')
        
        col = 1
        for pos in self.position_order:
            total = position_totals[pos]
            label = tk.Label(
                self.table_frame,
                text=str(total) if total > 0 else '-',
                bg=DARK_THEME['bg_hover'],
                fg=DARK_THEME['text_primary'],
                font=(DARK_THEME['font_family'], 10, 'bold'),
                padx=10,
                pady=5,
                anchor='center'
            )
            label.grid(row=row, column=col, sticky='ew')
            col += 1
        
        # Grand total
        grand_total_label = tk.Label(
            self.table_frame,
            text=str(grand_total) if grand_total > 0 else '-',
            bg=DARK_THEME['bg_hover'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10, 'bold'),
            padx=10,
            pady=5,
            anchor='center'
        )
        grand_total_label.grid(row=row, column=col, sticky='ew')