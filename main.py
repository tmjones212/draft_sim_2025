import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os

# Add the current directory to Python path for cross-platform compatibility
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

import config
from src.models import Team
from src.core import DraftEngine
from src.ui import DraftBoard, PlayerList, RosterView
from src.ui.theme import DARK_THEME
from src.ui.styled_widgets import StyledFrame, StyledButton
from src.utils import generate_mock_players


class MockDraftApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Mock Draft Simulator 2025")
        # Optimized window size
        self.root.geometry("1600x900")
        self.root.configure(bg=DARK_THEME['bg_primary'])
        
        # Set minimum window size
        self.root.minsize(1400, 800)
        
        # Initialize draft components
        self.teams = self._create_teams()
        self.draft_engine = DraftEngine(
            num_teams=config.num_teams,
            roster_spots=config.roster_spots,
            draft_type=config.draft_type,
            reversal_round=config.reversal_round
        )
        
        # Initialize players
        self.all_players = generate_mock_players()
        self.available_players = list(self.all_players)
        
        # Setup UI
        self.setup_ui()
        self.update_display()
    
    def _create_teams(self):
        teams = {}
        for i in range(1, config.num_teams + 1):
            teams[i] = Team(
                team_id=i,
                name=f"Team {i}",
                roster_spots=config.roster_spots
            )
        return teams
    
    def setup_ui(self):
        # Main container
        main_frame = StyledFrame(self.root, bg_type='primary')
        main_frame.pack(fill='both', expand=True, padx=15, pady=15)
        
        # Header section
        header_frame = StyledFrame(main_frame, bg_type='primary')
        header_frame.pack(fill='x', pady=(0, 15))
        
        # Title and status container
        status_container = StyledFrame(header_frame, bg_type='primary')
        status_container.pack(side='left', fill='x', expand=True)
        
        self.status_label = tk.Label(
            status_container,
            text="",
            bg=DARK_THEME['bg_primary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 18, 'bold')
        )
        self.status_label.pack(anchor='w')
        
        self.on_clock_label = tk.Label(
            status_container,
            text="",
            bg=DARK_THEME['bg_primary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 13)
        )
        self.on_clock_label.pack(anchor='w', pady=(3, 0))
        
        # Draft button
        self.draft_button = StyledButton(
            header_frame,
            text="DRAFT PLAYER",
            command=self.draft_player,
            bg=DARK_THEME['button_active'],
            font=(DARK_THEME['font_family'], 11, 'bold'),
            padx=25,
            pady=10
        )
        self.draft_button.pack(side='right')
        
        # Main content area - two row layout
        content_frame = StyledFrame(main_frame, bg_type='primary')
        content_frame.pack(fill='both', expand=True)
        
        # Configure grid
        content_frame.grid_rowconfigure(0, weight=3, minsize=400)  # Draft board and roster
        content_frame.grid_rowconfigure(1, weight=1, minsize=250)  # Available players
        content_frame.grid_columnconfigure(0, weight=5)  # Draft board column
        content_frame.grid_columnconfigure(1, weight=1, minsize=250)  # Roster column
        
        # Top row - Draft board and Roster
        # Draft board
        draft_panel = StyledFrame(content_frame, bg_type='secondary')
        draft_panel.grid(row=0, column=0, sticky='nsew', padx=(0, 10))
        
        total_rounds = sum(config.roster_spots.values())
        self.draft_board = DraftBoard(draft_panel, self.teams, total_rounds, max_visible_rounds=9)
        self.draft_board.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Roster panel (narrow)
        roster_panel = StyledFrame(content_frame, bg_type='secondary')
        roster_panel.grid(row=0, column=1, sticky='nsew')
        
        self.roster_view = RosterView(roster_panel, self.teams)
        self.roster_view.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Bottom row - Available players (spans both columns)
        player_panel = StyledFrame(content_frame, bg_type='secondary')
        player_panel.grid(row=1, column=0, columnspan=2, sticky='nsew', pady=(10, 0))
        
        self.player_list = PlayerList(player_panel)
        self.player_list.pack(fill='both', expand=True, padx=10, pady=10)
    
    def update_display(self):
        # Update status
        pick_num, round_num, pick_in_round, team_on_clock = self.draft_engine.get_current_pick_info()
        
        if self.draft_engine.is_draft_complete():
            self.status_label.config(text="Draft Complete!")
            self.on_clock_label.config(text="All picks have been made")
            self.draft_button.config(state="disabled", bg=DARK_THEME['button_bg'])
        else:
            self.status_label.config(text=f"Round {round_num} • Pick {pick_in_round}")
            self.on_clock_label.config(text=f"On the Clock: {self.teams[team_on_clock].name}")
        
        # Update components
        self.player_list.update_players(self.available_players)
        self.draft_board.update_picks(
            self.draft_engine.get_draft_results(),
            pick_num
        )
        self.roster_view.update_all_rosters()
    
    def draft_player(self):
        player = self.player_list.get_selected_player()
        if not player:
            messagebox.showwarning(
                "No Selection", 
                "Please select a player to draft.",
                parent=self.root
            )
            return
        
        _, _, _, team_on_clock = self.draft_engine.get_current_pick_info()
        current_team = self.teams[team_on_clock]
        
        try:
            self.draft_engine.make_pick(current_team, player)
            self.available_players.remove(player)
            self.update_display()
        except ValueError as e:
            messagebox.showerror(
                "Invalid Pick", 
                str(e),
                parent=self.root
            )


def main():
    root = tk.Tk()
    
    # Configure ttk styles for dark theme
    style = ttk.Style()
    style.theme_use('clam')
    
    # Configure colors
    style.configure('TFrame', background=DARK_THEME['bg_secondary'])
    style.configure('TLabel', background=DARK_THEME['bg_secondary'], foreground=DARK_THEME['text_primary'])
    style.configure('TNotebook', background=DARK_THEME['bg_secondary'], borderwidth=0)
    style.configure('TNotebook.Tab', 
                   background=DARK_THEME['bg_tertiary'],
                   foreground=DARK_THEME['text_secondary'],
                   padding=[12, 6])
    style.map('TNotebook.Tab',
             background=[('selected', DARK_THEME['bg_hover'])],
             foreground=[('selected', DARK_THEME['text_primary'])])
    
    MockDraftApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()