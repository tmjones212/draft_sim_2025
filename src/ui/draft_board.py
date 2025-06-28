import tkinter as tk
from tkinter import ttk
from typing import List, Dict, Optional
from ..core import DraftPick
from ..models import Team
from .theme import DARK_THEME, get_position_color
from .styled_widgets import StyledFrame


class DraftBoard(StyledFrame):
    def __init__(self, parent, teams: Dict[int, Team], total_rounds: int, max_visible_rounds: int = 9, **kwargs):
        super().__init__(parent, bg_type='secondary', **kwargs)
        self.teams = teams
        self.num_teams = len(teams)
        self.total_rounds = total_rounds
        self.max_visible_rounds = max_visible_rounds
        self.pick_widgets: Dict[int, tk.Frame] = {}  # pick_number -> widget
        self.current_pick_num = 1
        self.setup_ui()
        
    def setup_ui(self):
        # Main container with padding
        container = StyledFrame(self, bg_type='secondary')
        container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Canvas for vertical scrolling only
        canvas = tk.Canvas(
            container,
            bg=DARK_THEME['bg_secondary'],
            highlightthickness=0
        )
        v_scrollbar = tk.Scrollbar(
            container,
            orient='vertical',
            command=canvas.yview,
            bg=DARK_THEME['bg_tertiary'],
            troughcolor=DARK_THEME['bg_secondary']
        )
        
        self.scrollable_frame = StyledFrame(canvas, bg_type='secondary')
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=v_scrollbar.set)
        
        # Grid layout
        canvas.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)
        
        # Create the draft grid
        self.create_draft_grid()
    
    def create_draft_grid(self):
        # Column width and row height - adjusted for 10 teams
        col_width = 120  # Slightly wider for better readability
        row_height = 55  # More compact
        header_height = 40
        
        # Team headers
        for team_id in range(1, self.num_teams + 1):
            team = self.teams[team_id]
            
            header_frame = StyledFrame(
                self.scrollable_frame,
                bg_type='tertiary',
                relief='flat',
                width=col_width,
                height=header_height
            )
            header_frame.grid(row=0, column=team_id - 1, sticky='nsew', padx=2, pady=2)
            header_frame.grid_propagate(False)
            
            team_label = tk.Label(
                header_frame,
                text=team.name.upper(),
                bg=DARK_THEME['bg_tertiary'],
                fg=DARK_THEME['text_primary'],
                font=(DARK_THEME['font_family'], 11, 'bold')
            )
            team_label.place(relx=0.5, rely=0.5, anchor='center')
        
        # Create pick slots for visible rounds only
        pick_number = 1
        visible_rounds = min(self.total_rounds, self.max_visible_rounds)
        
        for round_num in range(1, self.total_rounds + 1):
            # Determine order for this round (with 3rd round reversal)
            if round_num == 1:
                order = list(range(1, self.num_teams + 1))
            elif round_num == 2:
                order = list(range(self.num_teams, 0, -1))
            elif round_num == 3:
                # 3rd round reversal - same direction as round 2
                order = list(range(self.num_teams, 0, -1))
            else:
                # After round 3, continue normal snake
                if round_num % 2 == 0:
                    order = list(range(self.num_teams, 0, -1))
                else:
                    order = list(range(1, self.num_teams + 1))
            
            # Create pick slots
            for pos, team_id in enumerate(order):
                pick_frame = StyledFrame(
                    self.scrollable_frame,
                    bg_type='tertiary',
                    relief='flat',
                    width=col_width,
                    height=row_height
                )
                pick_frame.grid(
                    row=round_num,
                    column=team_id - 1,
                    sticky='nsew',
                    padx=2,
                    pady=2
                )
                pick_frame.grid_propagate(False)
                
                # Round/Pick label
                round_pick_label = tk.Label(
                    pick_frame,
                    text=f"R{round_num}.{pos + 1}",
                    bg=DARK_THEME['bg_tertiary'],
                    fg=DARK_THEME['text_muted'],
                    font=(DARK_THEME['font_family'], 9)
                )
                round_pick_label.place(x=5, y=5)
                
                # Pick number label
                pick_num_label = tk.Label(
                    pick_frame,
                    text=f"#{pick_number}",
                    bg=DARK_THEME['bg_tertiary'],
                    fg=DARK_THEME['text_muted'],
                    font=(DARK_THEME['font_family'], 8)
                )
                pick_num_label.place(relx=0.95, y=5, anchor='ne')
                
                # Store reference
                self.pick_widgets[pick_number] = pick_frame
                pick_number += 1
        
        # Configure grid weights
        for i in range(self.num_teams):
            self.scrollable_frame.grid_columnconfigure(i, minsize=col_width)
        for i in range(self.total_rounds + 1):
            self.scrollable_frame.grid_rowconfigure(i, minsize=header_height if i == 0 else row_height)
    
    def update_picks(self, picks: List[DraftPick], current_pick_num: int):
        self.current_pick_num = current_pick_num
        
        # Update pick slots with drafted players
        for pick in picks:
            if pick.pick_number in self.pick_widgets:
                self.update_pick_slot(pick)
        
        # Highlight current pick
        self.highlight_current_pick()
    
    def update_pick_slot(self, pick: DraftPick):
        pick_frame = self.pick_widgets[pick.pick_number]
        
        # Clear existing player info (if any)
        for widget in pick_frame.winfo_children():
            if isinstance(widget, tk.Frame) and widget.winfo_y() > 20:
                widget.destroy()
        
        # Player container
        player_frame = StyledFrame(pick_frame, bg_type='tertiary')
        player_frame.place(x=5, y=25, relwidth=0.9)
        
        # Player name
        name_label = tk.Label(
            player_frame,
            text=pick.player.name,
            bg=DARK_THEME['bg_tertiary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10),
            anchor='w'
        )
        name_label.pack(fill='x')
        
        # Position badge
        pos_frame = tk.Frame(
            player_frame,
            bg=get_position_color(pick.player.position),
            padx=4,
            pady=1
        )
        pos_frame.pack(anchor='w', pady=(2, 0))
        
        pos_label = tk.Label(
            pos_frame,
            text=pick.player.position,
            bg=get_position_color(pick.player.position),
            fg='white',
            font=(DARK_THEME['font_family'], 8, 'bold')
        )
        pos_label.pack()
    
    def highlight_current_pick(self):
        # Remove previous highlights
        for pick_frame in self.pick_widgets.values():
            pick_frame.config(bg=DARK_THEME['bg_tertiary'], relief='flat')
        
        # Highlight current pick
        if self.current_pick_num in self.pick_widgets:
            current_frame = self.pick_widgets[self.current_pick_num]
            current_frame.config(
                bg=DARK_THEME['current_pick'],
                relief='solid',
                borderwidth=2
            )