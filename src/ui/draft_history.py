import tkinter as tk
from tkinter import ttk
from typing import List, Optional
from .theme import DARK_THEME, get_position_color
from .styled_widgets import StyledFrame
from ..models import Team, Player
from ..core import DraftPick


class DraftHistory(StyledFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg_type='secondary', **kwargs)
        self.draft_picks: List[DraftPick] = []
        self.teams: dict = {}
        self.setup_ui()
    
    def setup_ui(self):
        # Main container
        container = StyledFrame(self, bg_type='secondary')
        container.pack(fill='both', expand=True)
        
        # Header
        header_frame = StyledFrame(container, bg_type='secondary')
        header_frame.pack(fill='x', pady=(10, 0), padx=10)
        
        title = tk.Label(
            header_frame,
            text="DRAFT HISTORY",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 11, 'bold')
        )
        title.pack(side='left')
        
        # Filter controls
        filter_frame = StyledFrame(header_frame, bg_type='secondary')
        filter_frame.pack(side='right')
        
        # Round filter
        round_label = tk.Label(
            filter_frame,
            text="Round:",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 10)
        )
        round_label.pack(side='left', padx=(0, 5))
        
        self.round_var = tk.StringVar(value="All")
        self.round_dropdown = ttk.Combobox(
            filter_frame,
            textvariable=self.round_var,
            values=["All"],
            width=10,
            state='readonly'
        )
        self.round_dropdown.pack(side='left', padx=(0, 15))
        self.round_dropdown.bind('<<ComboboxSelected>>', lambda e: self.apply_filters())
        
        # Team filter
        team_label = tk.Label(
            filter_frame,
            text="Team:",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 10)
        )
        team_label.pack(side='left', padx=(0, 5))
        
        self.team_var = tk.StringVar(value="All")
        self.team_dropdown = ttk.Combobox(
            filter_frame,
            textvariable=self.team_var,
            values=["All"],
            width=15,
            state='readonly'
        )
        self.team_dropdown.pack(side='left', padx=(0, 15))
        self.team_dropdown.bind('<<ComboboxSelected>>', lambda e: self.apply_filters())
        
        # Position filter
        pos_label = tk.Label(
            filter_frame,
            text="Position:",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 10)
        )
        pos_label.pack(side='left', padx=(0, 5))
        
        self.position_var = tk.StringVar(value="All")
        self.position_dropdown = ttk.Combobox(
            filter_frame,
            textvariable=self.position_var,
            values=["All", "QB", "RB", "WR", "TE", "FLEX"],
            width=10,
            state='readonly'
        )
        self.position_dropdown.pack(side='left')
        self.position_dropdown.bind('<<ComboboxSelected>>', lambda e: self.apply_filters())
        
        # Scrollable draft list
        list_frame = StyledFrame(container, bg_type='secondary')
        list_frame.pack(fill='both', expand=True, padx=10, pady=(10, 10))
        
        # Canvas for scrolling
        self.canvas = tk.Canvas(
            list_frame,
            bg=DARK_THEME['bg_secondary'],
            highlightthickness=0
        )
        scrollbar = tk.Scrollbar(list_frame, orient='vertical', command=self.canvas.yview)
        
        self.picks_frame = tk.Frame(self.canvas, bg=DARK_THEME['bg_secondary'])
        self.picks_frame.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        
        self.canvas_window = self.canvas.create_window((0, 0), window=self.picks_frame, anchor='nw')
        
        # Make picks frame expand to canvas width
        def configure_canvas(event):
            canvas_width = event.width
            self.canvas.itemconfig(self.canvas_window, width=canvas_width)
        
        self.canvas.bind('<Configure>', configure_canvas)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Mouse wheel scrolling
        def on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), 'units')
        
        self.canvas.bind('<MouseWheel>', on_mousewheel)
        self.picks_frame.bind('<MouseWheel>', on_mousewheel)
    
    def update_draft_history(self, draft_picks: List[DraftPick], teams: dict):
        """Update the draft history display"""
        self.draft_picks = draft_picks
        self.teams = teams
        
        # Update filter dropdowns
        if draft_picks:
            # Update round filter
            rounds = sorted(set(pick.round for pick in draft_picks))
            round_values = ["All"] + [f"Round {r}" for r in rounds]
            self.round_dropdown['values'] = round_values
            
            # Update team filter
            team_names = ["All"] + sorted([team.name for team in teams.values()])
            self.team_dropdown['values'] = team_names
        
        self.apply_filters()
    
    def apply_filters(self):
        """Apply filters and refresh the display"""
        # Clear existing picks
        for widget in self.picks_frame.winfo_children():
            widget.destroy()
        
        # Filter picks
        filtered_picks = self.draft_picks[:]
        
        # Apply round filter
        if self.round_var.get() != "All":
            round_num = int(self.round_var.get().split()[-1])
            filtered_picks = [p for p in filtered_picks if p.round == round_num]
        
        # Apply team filter
        if self.team_var.get() != "All":
            team_name = self.team_var.get()
            team_id = None
            for tid, team in self.teams.items():
                if team.name == team_name:
                    team_id = tid
                    break
            if team_id:
                filtered_picks = [p for p in filtered_picks if p.team_id == team_id]
        
        # Apply position filter
        if self.position_var.get() != "All":
            if self.position_var.get() == "FLEX":
                filtered_picks = [p for p in filtered_picks if p.player.position in ["RB", "WR", "TE"]]
            else:
                filtered_picks = [p for p in filtered_picks if p.player.position == self.position_var.get()]
        
        # Display filtered picks
        for i, pick in enumerate(filtered_picks):
            self.create_pick_row(pick, i)
        
        # Update scroll region
        self.picks_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
    
    def create_pick_row(self, pick: DraftPick, index: int):
        """Create a row for a draft pick"""
        # Row frame
        row_bg = DARK_THEME['bg_tertiary'] if index % 2 == 0 else DARK_THEME['bg_secondary']
        row = tk.Frame(
            self.picks_frame,
            bg=row_bg,
            height=45
        )
        row.pack(fill='x', pady=1)
        row.pack_propagate(False)
        
        # Pick number
        pick_frame = tk.Frame(row, bg=row_bg, width=60)
        pick_frame.pack(side='left', fill='y')
        pick_frame.pack_propagate(False)
        
        pick_label = tk.Label(
            pick_frame,
            text=f"#{pick.pick_number}",
            bg=row_bg,
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 11, 'bold')
        )
        pick_label.pack(expand=True)
        
        # Round info
        round_frame = tk.Frame(row, bg=row_bg, width=80)
        round_frame.pack(side='left', fill='y')
        round_frame.pack_propagate(False)
        
        round_label = tk.Label(
            round_frame,
            text=f"Rd {pick.round}.{pick.pick_in_round:02d}",
            bg=row_bg,
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 10)
        )
        round_label.pack(expand=True)
        
        # Team name
        team = self.teams.get(pick.team_id)
        team_frame = tk.Frame(row, bg=row_bg, width=150)
        team_frame.pack(side='left', fill='y')
        team_frame.pack_propagate(False)
        
        team_label = tk.Label(
            team_frame,
            text=team.name if team else f"Team {pick.team_id}",
            bg=row_bg,
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10)
        )
        team_label.pack(expand=True)
        
        # Player info container
        player_container = tk.Frame(row, bg=row_bg)
        player_container.pack(side='left', fill='both', expand=True, padx=10)
        
        # Position badge
        pos_bg = get_position_color(pick.player.position)
        pos_label = tk.Label(
            player_container,
            text=pick.player.position,
            bg=pos_bg,
            fg='white',
            font=(DARK_THEME['font_family'], 9, 'bold'),
            padx=8,
            pady=2
        )
        pos_label.pack(side='left', pady=5)
        
        # Player name
        name_label = tk.Label(
            player_container,
            text=pick.player.format_name(),
            bg=row_bg,
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 11)
        )
        name_label.pack(side='left', padx=(10, 0))
        
        # Player stats
        stats_frame = tk.Frame(row, bg=row_bg, width=200)
        stats_frame.pack(side='right', fill='y', padx=10)
        stats_frame.pack_propagate(False)
        
        # ADP vs pick
        adp_text = f"ADP: {int(pick.player.adp)}" if pick.player.adp else "ADP: -"
        value = ""
        if pick.player.adp:
            diff = pick.player.adp - pick.pick_number
            if diff > 0:
                value = f" (+{int(diff)})"
            elif diff < 0:
                value = f" ({int(diff)})"
        
        stats_label = tk.Label(
            stats_frame,
            text=adp_text + value,
            bg=row_bg,
            fg=DARK_THEME['accent_success'] if value.startswith(" (+") else DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 10)
        )
        stats_label.pack(expand=True)
    
    def add_pick(self, pick: DraftPick):
        """Add a new pick to the history"""
        self.draft_picks.append(pick)
        self.update_draft_history(self.draft_picks, self.teams)
    
    def clear_history(self):
        """Clear all draft history"""
        self.draft_picks = []
        for widget in self.picks_frame.winfo_children():
            widget.destroy()